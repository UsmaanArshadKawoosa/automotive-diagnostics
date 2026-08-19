import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.crud import hybrid_search_knowledge_entries, search_knowledge_entries
from app.db.database import engine
from app.db.models import KnowledgeEntry
from tests.conftest import FakeEmbeddingService, FakeLLMService


class TestKnowledgeSearchIntegration:
    def test_search_returns_entries(self, db):
        embedding_service = FakeEmbeddingService()
        query_embedding = embedding_service.embed_query("misfire rough idle")
        rows = search_knowledge_entries(db, query_embedding=query_embedding, top_k=5)
        assert isinstance(rows, list)

    def test_knowledge_endpoint_search(self, client: TestClient):
        response = client.post(
            "/api/v1/knowledge/search",
            json={"query": "engine misfire", "top_k": 3},
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert isinstance(data["results"], list)


class TestHybridSearch:
    def test_exact_p0300_ranks_highly(self, db):
        embedding_service = FakeEmbeddingService()
        query_embedding = embedding_service.embed_query("P0300 engine misfire")

        p0300_entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.entry_key == "P0300").first()
        generic_entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.entry_key == "engine_misfire").first()

        with patch("app.crud.search_knowledge_entries") as mock_search:
            mock_search.return_value = [
                (p0300_entry, 0.3),
                (generic_entry, 0.1),
            ]
            rows = hybrid_search_knowledge_entries(db, query_embedding, "P0300 engine misfire", top_k=5)

        assert rows[0][0].entry_key == "P0300"
        assert rows[0][1] >= 0.9

    def test_exact_p0171_ranks_highly(self, db):
        embedding_service = FakeEmbeddingService()
        query_embedding = embedding_service.embed_query("P0171 system too lean")

        p0171_entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.entry_key == "P0171").first()
        generic_entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.entry_key == "engine_misfire").first()

        with patch("app.crud.search_knowledge_entries") as mock_search:
            mock_search.return_value = [
                (p0171_entry, 0.4),
                (generic_entry, 0.1),
            ]
            rows = hybrid_search_knowledge_entries(db, query_embedding, "P0171 system too lean", top_k=5)

        assert rows[0][0].entry_key == "P0171"
        assert rows[0][1] >= 0.9

    def test_exact_p0420_ranks_highly(self, db):
        embedding_service = FakeEmbeddingService()
        query_embedding = embedding_service.embed_query("P0420 catalytic converter")

        p0420_entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.entry_key == "P0420").first()
        generic_entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.entry_key == "engine_misfire").first()

        with patch("app.crud.search_knowledge_entries") as mock_search:
            mock_search.return_value = [
                (p0420_entry, 0.35),
                (generic_entry, 0.1),
            ]
            rows = hybrid_search_knowledge_entries(db, query_embedding, "P0420 catalytic converter", top_k=5)

        assert rows[0][0].entry_key == "P0420"
        assert rows[0][1] >= 0.9

    def test_symptom_only_semantic_search(self, db):
        embedding_service = FakeEmbeddingService()
        query_embedding = embedding_service.embed_query("engine runs rough and shakes at idle")

        rough_idle_entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.entry_key == "rough_idle").first()

        with patch("app.crud.search_knowledge_entries") as mock_search:
            mock_search.return_value = [
                (rough_idle_entry, 0.1),
            ]
            rows = hybrid_search_knowledge_entries(db, query_embedding, "engine runs rough and shakes at idle", top_k=5)

        assert len(rows) >= 1
        assert rows[0][0].entry_key == "rough_idle"
        assert rows[0][1] == pytest.approx(0.9, abs=0.01)

    def test_mixed_dtc_symptom_combines_signals(self, db):
        embedding_service = FakeEmbeddingService()
        query_embedding = embedding_service.embed_query("P0300 engine misfire")

        p0300_entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.entry_key == "P0300").first()
        rough_idle_entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.entry_key == "rough_idle").first()

        with patch("app.crud.search_knowledge_entries") as mock_search:
            mock_search.return_value = [
                (p0300_entry, 0.3),
                (rough_idle_entry, 0.1),
            ]
            rows = hybrid_search_knowledge_entries(db, query_embedding, "P0300 engine misfire", top_k=5)

        assert rows[0][0].entry_key == "P0300"
        assert rows[0][1] > rows[1][1]

    def test_keyword_only_does_not_destroy_semantic_relevance(self, db):
        embedding_service = FakeEmbeddingService()
        query_embedding = embedding_service.embed_query("P0300 engine misfire")

        p0300_entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.entry_key == "P0300").first()
        generic_misfire = db.query(KnowledgeEntry).filter(KnowledgeEntry.entry_key == "engine_misfire").first()

        with patch("app.crud.search_knowledge_entries") as mock_search:
            mock_search.return_value = [
                (generic_misfire, 0.05),
                (p0300_entry, 0.3),
            ]
            rows = hybrid_search_knowledge_entries(db, query_embedding, "P0300 engine misfire", top_k=5)

        assert rows[0][0].entry_key == "P0300"
        assert rows[0][1] > rows[1][1]

    def test_knowledge_ids_remain_intact(self, db):
        embedding_service = FakeEmbeddingService()
        query_embedding = embedding_service.embed_query("P0300")

        p0300_entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.entry_key == "P0300").first()
        expected_id = p0300_entry.id

        with patch("app.crud.search_knowledge_entries") as mock_search:
            mock_search.return_value = [
                (p0300_entry, 0.3),
            ]
            rows = hybrid_search_knowledge_entries(db, query_embedding, "P0300", top_k=5)

        assert len(rows) == 1
        assert rows[0][0].id == expected_id

    def test_evidence_validation_continues_working(self, client: TestClient, clean_diagnostic_tables):
        from app.services.diagnostic import DiagnosticService

        embedding_service = FakeEmbeddingService()
        llm_service = FakeLLMService()
        service = DiagnosticService(
            app_settings=embedding_service._settings,
            embedding_service=embedding_service,
            llm_service=llm_service,
        )

        payload = {
            "dtc_codes": ["P0300"],
            "symptom_text": "engine misfire",
        }
        response = client.post("/api/v1/diagnostics/analyze", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert len(data["hypotheses"]) >= 1
        hypothesis = data["hypotheses"][0]
        assert "knowledge_references" in hypothesis
        evidence_ids = {item["id"] for item in data["evidence"]}
        for ref in hypothesis["knowledge_references"]:
            assert ref in evidence_ids
