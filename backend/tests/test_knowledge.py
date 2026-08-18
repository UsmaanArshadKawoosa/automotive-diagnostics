from fastapi.testclient import TestClient

from app.crud import search_knowledge_entries
from app.db.database import engine
from app.db.models import KnowledgeEntry
from tests.conftest import FakeEmbeddingService


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


class TestKnowledgeModelConsistency:
    def test_knowledge_entries_have_embeddings(self, db):
        entries = db.query(KnowledgeEntry).all()
        for entry in entries:
            assert entry.embedding is not None
            assert len(entry.embedding) == 384
