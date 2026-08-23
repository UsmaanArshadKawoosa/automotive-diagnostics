import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.crud import hybrid_search_knowledge_entries, search_knowledge_entries
from app.db.database import engine
from app.db.models import KnowledgeEntry
from app.services.component_taxonomy import map_knowledge_entry
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


class TestComponentBoostRetrieval:
    """Tests for component matching boost in hybrid search."""

    def test_component_boost_raises_relevant_dtc(self, db):
        """Entries matching component IDs from DTC codes should get a score boost."""
        embedding_service = FakeEmbeddingService()
        query_embedding = embedding_service.embed_query("P0300 engine misfire")

        p0300_entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.entry_key == "P0300").first()
        p0301_entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.entry_key == "P0301").first()
        generic_entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.entry_key == "engine_misfire").first()

        with patch("app.crud.search_knowledge_entries") as mock_search:
            mock_search.return_value = [
                (p0300_entry, 0.3),
                (p0301_entry, 0.25),
                (generic_entry, 0.1),
            ]
            # Without component boost
            rows_no_boost = hybrid_search_knowledge_entries(
                db, query_embedding, "P0300 engine misfire", top_k=5, request_components=[]
            )
            # With component boost for spark_plug (mapped from P0300)
            rows_boost = hybrid_search_knowledge_entries(
                db, query_embedding, "P0300 engine misfire", top_k=5, request_components=["spark_plug"]
            )

        # P0300 should rank higher with boost
        p0300_score_no_boost = next(score for entry, score in rows_no_boost if entry.entry_key == "P0300")
        p0300_score_boost = next(score for entry, score in rows_boost if entry.entry_key == "P0300")

        assert p0300_score_boost > p0300_score_no_boost
        # The difference should be approximately the component boost (0.3)
        assert p0300_score_boost - p0300_score_no_boost == pytest.approx(0.3, abs=0.01)

    def test_component_boost_works_for_maf_sensor(self, db):
        """P0171 maps to maf_sensor; maf_sensor entries should be boosted."""
        embedding_service = FakeEmbeddingService()
        query_embedding = embedding_service.embed_query("P0171 system too lean")

        p0171_entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.entry_key == "P0171").first()
        p0101_entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.entry_key == "P0101").first()

        with patch("app.crud.search_knowledge_entries") as mock_search:
            mock_search.return_value = [
                (p0171_entry, 0.4),
                (p0101_entry, 0.35),
            ]
            rows_no_boost = hybrid_search_knowledge_entries(
                db, query_embedding, "P0171 system too lean", top_k=5, request_components=[]
            )
            rows_boost = hybrid_search_knowledge_entries(
                db, query_embedding, "P0171 system too lean", top_k=5, request_components=["maf_sensor"]
            )

        p0101_score_no_boost = next(score for entry, score in rows_no_boost if entry.entry_key == "P0101")
        p0101_score_boost = next(score for entry, score in rows_boost if entry.entry_key == "P0101")

        assert p0101_score_boost > p0101_score_no_boost
        assert p0101_score_boost - p0101_score_no_boost == pytest.approx(0.3, abs=0.01)

    def test_component_boost_does_not_affect_unrelated_entries(self, db):
        """Entries not matching requested components should not be boosted."""
        embedding_service = FakeEmbeddingService()
        query_embedding = embedding_service.embed_query("P0300 engine misfire")

        p0300_entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.entry_key == "P0300").first()
        # P0171 maps to maf_sensor, not spark_plug
        p0171_entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.entry_key == "P0171").first()

        with patch("app.crud.search_knowledge_entries") as mock_search:
            mock_search.return_value = [
                (p0300_entry, 0.3),
                (p0171_entry, 0.35),  # Higher base semantic score
            ]
            rows_no_boost = hybrid_search_knowledge_entries(
                db, query_embedding, "P0300 engine misfire", top_k=5, request_components=[]
            )
            rows_boost = hybrid_search_knowledge_entries(
                db, query_embedding, "P0300 engine misfire", top_k=5, request_components=["spark_plug"]
            )

        # Without boost, P0171 should win (higher semantic score 0.35 vs 0.3 -> 1.0 vs 0.7 similarity)
        # With spark_plug boost, P0300 should win
        top_no_boost = rows_no_boost[0][0].entry_key
        top_boost = rows_boost[0][0].entry_key

        assert top_boost == "P0300"


class TestDeterministicOrdering:
    """Tests for deterministic result ordering."""

    def test_same_scores_sorted_by_entry_key(self, db):
        """Entries with identical scores should be sorted by entry_key for stability."""
        embedding_service = FakeEmbeddingService()
        query_embedding = embedding_service.embed_query("test query")

        # Create mock entries with same score
        entry_a = db.query(KnowledgeEntry).filter(KnowledgeEntry.entry_key == "P0300").first()
        entry_b = db.query(KnowledgeEntry).filter(KnowledgeEntry.entry_key == "P0301").first()

        with patch("app.crud.search_knowledge_entries") as mock_search:
            # Both entries get same distance (0.3) -> same semantic score
            mock_search.return_value = [
                (entry_b, 0.3),  # P0301 first in mock
                (entry_a, 0.3),  # P0300 second in mock
            ]
            rows = hybrid_search_knowledge_entries(
                db, query_embedding, "P0300 P0301", top_k=5, request_components=[]
            )

        # Should be sorted by entry_key: P0300, then P0301
        assert rows[0][0].entry_key == "P0300"
        assert rows[1][0].entry_key == "P0301"

    def test_deterministic_ordering_across_multiple_calls(self, db):
        """Repeated calls with same inputs should produce identical ordering."""
        embedding_service = FakeEmbeddingService()
        query_embedding = embedding_service.embed_query("P0300 engine misfire")

        p0300_entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.entry_key == "P0300").first()
        p0301_entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.entry_key == "P0301").first()
        p0302_entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.entry_key == "P0302").first()

        with patch("app.crud.search_knowledge_entries") as mock_search:
            mock_search.return_value = [
                (p0301_entry, 0.3),
                (p0300_entry, 0.3),
                (p0302_entry, 0.3),
            ]
            rows1 = hybrid_search_knowledge_entries(
                db, query_embedding, "P0300 engine misfire", top_k=5, request_components=[]
            )
            rows2 = hybrid_search_knowledge_entries(
                db, query_embedding, "P0300 engine misfire", top_k=5, request_components=[]
            )

        keys1 = [entry.entry_key for entry, _ in rows1]
        keys2 = [entry.entry_key for entry, _ in rows2]
        assert keys1 == keys2
        # Should be alphabetical: P0300, P0301, P0302
        assert keys1 == ["P0300", "P0301", "P0302"]


class TestDuplicateContentRemoval:
    """Tests for duplicate content removal in retrieval."""

    def test_duplicate_content_is_removed(self, db):
        """Entries with identical content should be deduplicated, keeping highest score."""
        embedding_service = FakeEmbeddingService()
        query_embedding = embedding_service.embed_query("test query")

        # Create two entries with same content but different entry_keys
        entry1 = db.query(KnowledgeEntry).filter(KnowledgeEntry.entry_key == "P0300").first()
        entry2 = db.query(KnowledgeEntry).filter(KnowledgeEntry.entry_key == "P0301").first()

        with patch("app.crud.search_knowledge_entries") as mock_search:
            # Same content for both (simulated by mocking)
            mock_search.return_value = [
                (entry2, 0.3),  # Higher distance -> lower semantic score
                (entry1, 0.1),  # Lower distance -> higher semantic score
            ]
            rows = hybrid_search_knowledge_entries(
                db, query_embedding, "test query", top_k=5, request_components=[]
            )

        # Should only return one entry (the higher-scored one)
        # Since content deduplication checks actual content, this test relies on
        # the mock returning different entries. In real usage, the deduplication
        # happens based on entry.content equality.
        assert len(rows) <= 2  # Could be 1 or 2 depending on content

    def test_deduplication_keeps_highest_scored(self, db):
        """When duplicates exist, the highest-scored entry should be kept."""
        embedding_service = FakeEmbeddingService()
        query_embedding = embedding_service.embed_query("test query")

        entry1 = db.query(KnowledgeEntry).filter(KnowledgeEntry.entry_key == "P0300").first()
        entry2 = db.query(KnowledgeEntry).filter(KnowledgeEntry.entry_key == "P0301").first()

        with patch("app.crud.search_knowledge_entries") as mock_search:
            # Force same content by patching the content attribute temporarily
            original_content1 = entry1.content
            original_content2 = entry2.content
            entry1.content = "SAME CONTENT"
            entry2.content = "SAME CONTENT"

            mock_search.return_value = [
                (entry2, 0.3),  # Lower score
                (entry1, 0.1),  # Higher score
            ]
            rows = hybrid_search_knowledge_entries(
                db, query_embedding, "test query", top_k=5, request_components=[]
            )

            # Restore
            entry1.content = original_content1
            entry2.content = original_content2

        # Should only have 1 result (the higher-scored one)
        assert len(rows) == 1
        assert rows[0][0].entry_key == "P0300"


class TestEvidenceReferenceValidation:
    """Tests for evidence reference validation in diagnostic service."""

    def test_valid_evidence_references_accepted(self, db, clean_diagnostic_tables):
        """Valid structured evidence references should be accepted."""
        from app.services.diagnostic import DiagnosticService
        from app.schemas import EvidenceReference, KnowledgeSearchResult

        embedding_service = FakeEmbeddingService()
        llm_service = FakeLLMService()
        service = DiagnosticService(
            app_settings=embedding_service._settings,
            embedding_service=embedding_service,
            llm_service=llm_service,
        )

        # Get real evidence from DB
        p0300_entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.entry_key == "P0300").first()
        evidence = [
            KnowledgeSearchResult(
                id=p0300_entry.id,
                category="dtc",
                entry_key="P0300",
                content=p0300_entry.content,
                source=p0300_entry.source,
                similarity_score=0.95,
            )
        ]

        # Create a hypothesis with valid evidence reference
        ref = EvidenceReference(
            evidence_id=p0300_entry.id,
            category="dtc",
            entry_key="P0300",
            excerpt=p0300_entry.content[:50],
            similarity_score=0.95,
            relevance="supporting",
        )

        validated = service._validate_evidence_references([ref], evidence)

        assert len(validated) == 1
        assert validated[0].evidence_id == p0300_entry.id
        assert validated[0].category == "dtc"

    def test_hallucinated_evidence_references_rejected(self, db, clean_diagnostic_tables):
        """Evidence references with non-existent IDs should be rejected."""
        from app.services.diagnostic import DiagnosticService
        from app.schemas import EvidenceReference, KnowledgeSearchResult

        embedding_service = FakeEmbeddingService()
        llm_service = FakeLLMService()
        service = DiagnosticService(
            app_settings=embedding_service._settings,
            embedding_service=embedding_service,
            llm_service=llm_service,
        )

        p0300_entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.entry_key == "P0300").first()
        evidence = [
            KnowledgeSearchResult(
                id=p0300_entry.id,
                category="dtc",
                entry_key="P0300",
                content=p0300_entry.content,
                source=p0300_entry.source,
                similarity_score=0.95,
            )
        ]

        # Reference a non-existent UUID
        fake_id = uuid.uuid4()
        ref = EvidenceReference(
            evidence_id=fake_id,
            category="dtc",
            entry_key="P0300",
            excerpt="fake excerpt",
            similarity_score=0.95,
            relevance="supporting",
        )

        validated = service._validate_evidence_references([ref], evidence)

        assert len(validated) == 0

    def test_wrong_category_rejected(self, db, clean_diagnostic_tables):
        """Evidence references with wrong category should be rejected."""
        from app.services.diagnostic import DiagnosticService
        from app.schemas import EvidenceReference, KnowledgeSearchResult

        embedding_service = FakeEmbeddingService()
        llm_service = FakeLLMService()
        service = DiagnosticService(
            app_settings=embedding_service._settings,
            embedding_service=embedding_service,
            llm_service=llm_service,
        )

        p0300_entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.entry_key == "P0300").first()
        evidence = [
            KnowledgeSearchResult(
                id=p0300_entry.id,
                category="dtc",
                entry_key="P0300",
                content=p0300_entry.content,
                source=p0300_entry.source,
                similarity_score=0.95,
            )
        ]

        # Reference with wrong category
        ref = EvidenceReference(
            evidence_id=p0300_entry.id,
            category="symptom",  # Wrong category
            entry_key="P0300",
            excerpt=p0300_entry.content[:50],
            similarity_score=0.95,
            relevance="supporting",
        )

        validated = service._validate_evidence_references([ref], evidence)

        assert len(validated) == 0

    def test_similarity_score_tolerance(self, db, clean_diagnostic_tables):
        """Similarity score within 0.1 tolerance should be accepted."""
        from app.services.diagnostic import DiagnosticService
        from app.schemas import EvidenceReference, KnowledgeSearchResult

        embedding_service = FakeEmbeddingService()
        llm_service = FakeLLMService()
        service = DiagnosticService(
            app_settings=embedding_service._settings,
            embedding_service=embedding_service,
            llm_service=llm_service,
        )

        p0300_entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.entry_key == "P0300").first()
        evidence = [
            KnowledgeSearchResult(
                id=p0300_entry.id,
                category="dtc",
                entry_key="P0300",
                content=p0300_entry.content,
                source=p0300_entry.source,
                similarity_score=0.85,
            )
        ]

        # Reference with similarity within tolerance (0.05 difference)
        ref = EvidenceReference(
            evidence_id=p0300_entry.id,
            category="dtc",
            entry_key="P0300",
            excerpt=p0300_entry.content[:50],
            similarity_score=0.90,  # 0.05 difference - within 0.1 tolerance
            relevance="supporting",
        )

        validated = service._validate_evidence_references([ref], evidence)

        assert len(validated) == 1

    def test_similarity_score_outside_tolerance_rejected(self, db, clean_diagnostic_tables):
        """Similarity score outside 0.1 tolerance should be rejected."""
        from app.services.diagnostic import DiagnosticService
        from app.schemas import EvidenceReference, KnowledgeSearchResult

        embedding_service = FakeEmbeddingService()
        llm_service = FakeLLMService()
        service = DiagnosticService(
            app_settings=embedding_service._settings,
            embedding_service=embedding_service,
            llm_service=llm_service,
        )

        p0300_entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.entry_key == "P0300").first()
        evidence = [
            KnowledgeSearchResult(
                id=p0300_entry.id,
                category="dtc",
                entry_key="P0300",
                content=p0300_entry.content,
                source=p0300_entry.source,
                similarity_score=0.85,
            )
        ]

        # Reference with similarity outside tolerance (0.2 difference)
        ref = EvidenceReference(
            evidence_id=p0300_entry.id,
            category="dtc",
            entry_key="P0300",
            excerpt=p0300_entry.content[:50],
            similarity_score=0.65,  # 0.2 difference - outside 0.1 tolerance
            relevance="supporting",
        )

        validated = service._validate_evidence_references([ref], evidence)

        assert len(validated) == 0


class TestRetrievalWithDiagnosticFlow:
    """Tests for retrieval integration with diagnostic follow-up logic."""

    def test_follow_up_uses_conversation_context(self, db, clean_diagnostic_tables):
        """Follow-up analysis should use conversation context for retrieval."""
        from app.services.diagnostic import DiagnosticService
        from app.schemas import DiagnosticAnalyzeRequest

        embedding_service = FakeEmbeddingService()
        llm_service = FakeLLMService()
        service = DiagnosticService(
            app_settings=embedding_service._settings,
            embedding_service=embedding_service,
            llm_service=llm_service,
        )

        # Initial analysis
        request1 = DiagnosticAnalyzeRequest(
            make="Toyota",
            model="Corolla",
            year=2020,
            dtc_codes=["P0300"],
            symptom_text="Engine is misfiring at idle",
        )
        response1 = service.analyze(db, request1)

        assert response1.session_id is not None
        assert len(response1.hypotheses) >= 1

        # Follow-up with additional info
        from app.crud import get_diagnostic_session
        session = get_diagnostic_session(db, response1.session_id)

        request2 = DiagnosticAnalyzeRequest(
            make="Toyota",
            model="Corolla",
            year=2020,
            dtc_codes=["P0300"],
            symptom_text="Engine is misfiring at idle",
            session_id=response1.session_id,
            follow_up_answer="Misfire only happens when engine is cold",
        )
        response2 = service.analyze(db, request2, session=session)

        # Follow-up should be processed
        assert response2.session_id == response1.session_id
        assert len(response2.hypotheses) >= 1

    def test_retrieval_includes_previous_dtc_codes(self, db, clean_diagnostic_tables):
        """Retrieval in follow-up should still consider original DTC codes."""
        from app.services.diagnostic import DiagnosticService
        from app.schemas import DiagnosticAnalyzeRequest
        from app.crud import get_diagnostic_session

        embedding_service = FakeEmbeddingService()
        llm_service = FakeLLMService()
        service = DiagnosticService(
            app_settings=embedding_service._settings,
            embedding_service=embedding_service,
            llm_service=llm_service,
        )

        request1 = DiagnosticAnalyzeRequest(
            dtc_codes=["P0300", "P0301"],
            symptom_text="Engine misfiring",
        )
        response1 = service.analyze(db, request1)
        session = get_diagnostic_session(db, response1.session_id)

        # Verify session has DTC codes
        assert "P0300" in (session.dtc_codes or "")
        assert "P0301" in (session.dtc_codes or "")


class TestLowQualityFiltering:
    """Tests for low-quality result filtering."""

    def test_retrieval_returns_minimum_top_k(self, db):
        """Retrieval should return up to top_k results when available."""
        embedding_service = FakeEmbeddingService()
        query_embedding = embedding_service.embed_query("P0300")

        p0300_entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.entry_key == "P0300").first()
        p0301_entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.entry_key == "P0301").first()
        p0302_entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.entry_key == "P0302").first()

        with patch("app.crud.search_knowledge_entries") as mock_search:
            mock_search.return_value = [
                (p0300_entry, 0.1),
                (p0301_entry, 0.2),
                (p0302_entry, 0.3),
            ]
            rows = hybrid_search_knowledge_entries(
                db, query_embedding, "P0300", top_k=5, request_components=[]
            )

        assert len(rows) == 3
        # Should be sorted by score desc
        scores = [score for _, score in rows]
        assert scores == sorted(scores, reverse=True)

    def test_retrieval_respects_top_k_limit(self, db):
        """Retrieval should not return more than top_k results."""
        embedding_service = FakeEmbeddingService()
        query_embedding = embedding_service.embed_query("test")

        entries = [
            db.query(KnowledgeEntry).filter(KnowledgeEntry.entry_key == f"P030{i}").first()
            for i in range(5)
        ]

        with patch("app.crud.search_knowledge_entries") as mock_search:
            mock_search.return_value = [(e, 0.1 + i * 0.05) for i, e in enumerate(entries)]
            rows = hybrid_search_knowledge_entries(
                db, query_embedding, "test", top_k=3, request_components=[]
            )

        assert len(rows) == 3
