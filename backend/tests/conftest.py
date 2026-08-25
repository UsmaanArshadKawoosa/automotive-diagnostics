import json
import uuid
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings, settings
from app.db.database import get_db
from app.main import app
from app.schemas import DiagnosticHypothesis
from app.services.embeddings import EmbeddingService, get_embedding_service
from app.services.knowledge_ingestion import KnowledgeIngestionService
from app.services.knowledge_loader import KnowledgeLoader
from app.services.llm import LLMProvider, LLMService, get_llm_service

TEST_EMBEDDING_DIMENSIONS = 384


class FakeEmbeddingService(EmbeddingService):
    def __init__(self) -> None:
        self._settings = Settings()

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[1.0 if i == 0 else 0.0 for i in range(TEST_EMBEDDING_DIMENSIONS)] for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        return [1.0 if i == 0 else 0.0 for i in range(TEST_EMBEDDING_DIMENSIONS)]


class FakeLLMProvider(LLMProvider):
    def __init__(self, response: str | None = None) -> None:
        self._response = response or self._default_response()

    def _default_response(self) -> str:
        hypothesis = DiagnosticHypothesis(
            fault_description="Faulty spark plugs",
            confidence_score=0.75,
            severity="medium",
            supporting_evidence=["Retrieved knowledge indicates misfire"],
            recommended_checks=["Inspect spark plugs"],
            repair_suggestion="Replace spark plugs if worn",
        )
        return json.dumps({
            "status": "complete",
            "follow_up_question": None,
            "follow_up_reason": None,
            "hypotheses": [hypothesis.model_dump()]
        })

    def complete(self, prompt: str, response_schema: dict[str, Any] | None = None) -> str:
        return self._response


class FakeLLMService(LLMService):
    def __init__(self, response: str | None = None) -> None:
        self._provider = FakeLLMProvider(response)

    def complete(self, prompt: str, response_schema: dict[str, Any] | None = None) -> str:
        return self._provider.complete(prompt, response_schema)


@pytest.fixture(scope="session", autouse=True)
def seed_knowledge_base(engine):
    with engine.connect() as conn:
        result = conn.execute(text("SELECT count(*) FROM knowledge_entries"))
        count = result.scalar()
    if count > 0:
        return

    fake_emb = FakeEmbeddingService()
    knowledge_dir = Path(__file__).resolve().parent.parent.parent / "knowledge_base"
    loader = KnowledgeLoader(knowledge_dir)

    with Session(engine) as session:
        service = KnowledgeIngestionService(session, fake_emb, loader)
        result = service.ingest_from_loader(skip_existing=False)
        session.commit()


@pytest.fixture(scope="session")
def engine():
    return create_engine(settings.sqlalchemy_database_url, pool_pre_ping=True)


@pytest.fixture(scope="function")
def db(engine) -> Generator[Session, None, None]:
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="function")
def clean_diagnostic_tables(engine):
    with engine.connect() as conn:
        conn.execute(text("TRUNCATE TABLE diagnostic_results, diagnostic_sessions, confirmed_diagnostic_cases RESTART IDENTITY CASCADE"))
        conn.commit()
    yield


@pytest.fixture
def fake_embedding_service() -> FakeEmbeddingService:
    return FakeEmbeddingService()


@pytest.fixture
def fake_llm_service() -> FakeLLMService:
    return FakeLLMService()


@pytest.fixture
def client(fake_embedding_service, fake_llm_service) -> Generator[TestClient, None, None]:
    test_engine = create_engine(settings.sqlalchemy_database_url, pool_pre_ping=True)
    TestingSessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_embedding_service] = lambda: fake_embedding_service
    app.dependency_overrides[get_llm_service] = lambda: fake_llm_service
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    test_engine.dispose()
