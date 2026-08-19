import json
import shutil
import tempfile
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db.models import KnowledgeEntry
from app.schemas import KnowledgeEntryCreate
from app.services.embeddings import EmbeddingService
from app.services.knowledge_ingestion import KnowledgeIngestionService
from app.services.knowledge_loader import KnowledgeLoader, KnowledgeLoaderError


class FakeEmbeddingServiceForIngestion(EmbeddingService):
    def __init__(self, dimensions: int = 384) -> None:
        self._settings = object()
        self._dimensions = dimensions

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[1.0 if i == 0 else 0.0 for i in range(self._dimensions)] for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        return [1.0 if i == 0 else 0.0 for i in range(self._dimensions)]


@pytest.fixture
def temp_dir():
    base = Path(__file__).resolve().parent / ".pytest_tmp"
    base.mkdir(exist_ok=True)
    path = Path(tempfile.mkdtemp(prefix="knowledge_", dir=base))
    yield path
    shutil.rmtree(path, ignore_errors=True)


class TestKnowledgeLoader:
    def test_load_json_array(self, temp_dir: Path):
        file_path = temp_dir / "entries.json"
        file_path.write_text(
            json.dumps(
                [
                    {
                        "category": "symptom",
                        "entry_key": "rough_idle",
                        "content": "Rough idle description",
                        "source": "test",
                    }
                ]
            )
        )
        loader = KnowledgeLoader(temp_dir)
        entries = loader.load()
        assert len(entries) == 1
        assert entries[0].category == "symptom"
        assert entries[0].entry_key == "rough_idle"

    def test_load_jsonl(self, temp_dir: Path):
        file_path = temp_dir / "entries.jsonl"
        file_path.write_text(
            json.dumps({"category": "dtc", "entry_key": "P0300", "content": "Misfire", "source": "test"})
            + "\n"
            + json.dumps({"category": "fault", "entry_key": "coil", "content": "Coil fault", "source": "test"})
            + "\n"
        )
        loader = KnowledgeLoader(temp_dir)
        entries = loader.load()
        assert len(entries) == 2
        assert entries[0].entry_key == "P0300"
        assert entries[1].entry_key == "coil"

    def test_load_invalid_json_raises(self, temp_dir: Path):
        file_path = temp_dir / "bad.json"
        file_path.write_text("not json")
        loader = KnowledgeLoader(temp_dir)
        with pytest.raises(KnowledgeLoaderError, match="Invalid JSON"):
            loader.load()

    def test_load_invalid_schema_raises(self, temp_dir: Path):
        file_path = temp_dir / "bad.json"
        file_path.write_text(json.dumps([{"category": "symptom"}]))
        loader = KnowledgeLoader(temp_dir)
        with pytest.raises(KnowledgeLoaderError, match="Invalid knowledge entry"):
            loader.load()

    def test_load_missing_directory_raises(self, temp_dir: Path):
        loader = KnowledgeLoader(temp_dir / "does_not_exist")
        with pytest.raises(KnowledgeLoaderError, match="does not exist"):
            loader.load()


class TestKnowledgeIngestionService:
    def _unique_key(self) -> str:
        return f"test_{uuid.uuid4().hex[:8]}"

    def test_ingest_creates_entries(self, db):
        embedding_service = FakeEmbeddingServiceForIngestion()
        service = KnowledgeIngestionService(db, embedding_service)
        key = self._unique_key()
        entries = [
            KnowledgeEntryCreate(
                category="symptom", entry_key=f"{key}_misfire", content="Engine misfire", source="test"
            ),
            KnowledgeEntryCreate(
                category="dtc", entry_key=f"{key}_dtc", content="Random misfire", source="test"
            ),
        ]
        result = service.ingest(entries)
        assert result.created == 2
        assert result.skipped == 0
        assert result.errors == []

        stored = db.query(KnowledgeEntry).filter(KnowledgeEntry.entry_key.like(f"{key}%")).all()
        assert len(stored) == 2
        assert all(entry.embedding is not None for entry in stored)

    def test_ingest_skips_existing(self, db):
        embedding_service = FakeEmbeddingServiceForIngestion()
        service = KnowledgeIngestionService(db, embedding_service)
        key = self._unique_key()
        entries = [
            KnowledgeEntryCreate(
                category="symptom", entry_key=f"{key}_skip", content="Engine misfire", source="test"
            )
        ]
        service.ingest(entries)
        result = service.ingest(entries, skip_existing=True)
        assert result.created == 0
        assert result.skipped == 1

    def test_ingest_empty_returns_zero(self, db):
        embedding_service = FakeEmbeddingServiceForIngestion()
        service = KnowledgeIngestionService(db, embedding_service)
        result = service.ingest([])
        assert result.created == 0
        assert result.skipped == 0


class TestKnowledgeBulkEndpoint:
    def _unique_key(self) -> str:
        return f"bulk_{uuid.uuid4().hex[:8]}"

    def test_bulk_create(self, client: TestClient):
        key = self._unique_key()
        payload = {
            "entries": [
                {
                    "category": "symptom",
                    "entry_key": key,
                    "content": "Engine hesitates on acceleration",
                    "source": "test",
                }
            ]
        }
        response = client.post("/api/v1/knowledge/bulk", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["created"] == 1
        assert data["skipped"] == 0
        assert data["errors"] == []

    def test_bulk_create_skips_duplicates(self, client: TestClient):
        key = self._unique_key()
        payload = {
            "entries": [
                {
                    "category": "symptom",
                    "entry_key": key,
                    "content": "Duplicate entry",
                    "source": "test",
                }
            ]
        }
        response = client.post("/api/v1/knowledge/bulk", json=payload)
        assert response.status_code == 201
        assert response.json()["created"] == 1

        response = client.post("/api/v1/knowledge/bulk", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["created"] == 0
        assert data["skipped"] == 1
