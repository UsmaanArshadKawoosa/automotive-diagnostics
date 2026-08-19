import json
import uuid

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.schemas import DiagnosticHypothesis, KnowledgeSearchResult
from app.services.diagnostic import DiagnosticService
from app.services.embeddings import EmbeddingService
from app.services.llm import LLMProvider, LLMService


class FakeEmbeddingServiceForValidation(EmbeddingService):
    def __init__(self) -> None:
        self._settings = Settings()

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[1.0 if i == 0 else 0.0 for i in range(384)] for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        return [1.0 if i == 0 else 0.0 for i in range(384)]


class FakeLLMProviderForValidation(LLMProvider):
    def __init__(self, hypothesis: DiagnosticHypothesis) -> None:
        self._response = json.dumps({"hypotheses": [hypothesis.model_dump()]})

    def complete(self, prompt: str, response_schema: dict | None = None) -> str:
        return self._response


class FakeLLMServiceForValidation(LLMService):
    def __init__(self, hypothesis: DiagnosticHypothesis) -> None:
        self._provider = FakeLLMProviderForValidation(hypothesis)

    def complete(self, prompt: str, response_schema: dict | None = None) -> str:
        return self._provider.complete(prompt, response_schema)


class TestEvidenceValidation:
    def _make_service(self, hypothesis: DiagnosticHypothesis) -> DiagnosticService:
        embedding_service = FakeEmbeddingServiceForValidation()
        llm_service = FakeLLMServiceForValidation(hypothesis)
        return DiagnosticService(
            app_settings=embedding_service._settings,
            embedding_service=embedding_service,
            llm_service=llm_service,
        )

    def test_valid_evidence_reference_persists(self, db, clean_diagnostic_tables):
        entry_id = uuid.uuid4()
        evidence = [
            KnowledgeSearchResult(
                id=entry_id,
                category="symptom",
                entry_key="engine_misfire",
                content="Engine misfire is often caused by faulty spark plugs.",
                source="test",
                similarity_score=0.9,
            )
        ]

        # Patch the evidence retrieval by directly invoking _validate_evidence.
        service = self._make_service(
            DiagnosticHypothesis(
                fault_description="Faulty spark plugs",
                confidence_score=0.8,
                severity="medium",
                supporting_evidence=["[symptom] engine_misfire"],
                recommended_checks=["Inspect spark plugs"],
            )
        )
        hypothesis = DiagnosticHypothesis(
            fault_description="Faulty spark plugs",
            confidence_score=0.8,
            severity="medium",
            supporting_evidence=["[symptom] engine_misfire"],
            recommended_checks=["Inspect spark plugs"],
        )
        validated_strings, validated_ids = service._validate_evidence(hypothesis, evidence)

        assert validated_strings == ["[symptom] engine_misfire"]
        assert validated_ids == [entry_id]

    def test_hallucinated_evidence_reference_is_filtered(self, db, clean_diagnostic_tables):
        entry_id = uuid.uuid4()
        evidence = [
            KnowledgeSearchResult(
                id=entry_id,
                category="symptom",
                entry_key="engine_misfire",
                content="Engine misfire is often caused by faulty spark plugs.",
                source="test",
                similarity_score=0.9,
            )
        ]

        service = self._make_service(
            DiagnosticHypothesis(
                fault_description="Faulty spark plugs",
                confidence_score=0.8,
                severity="medium",
                supporting_evidence=["[symptom] engine_misfire", "Made up reference"],
                recommended_checks=["Inspect spark plugs"],
            )
        )
        hypothesis = DiagnosticHypothesis(
            fault_description="Faulty spark plugs",
            confidence_score=0.8,
            severity="medium",
            supporting_evidence=["[symptom] engine_misfire", "Made up reference"],
            recommended_checks=["Inspect spark plugs"],
        )
        validated_strings, validated_ids = service._validate_evidence(hypothesis, evidence)

        assert validated_strings == ["[symptom] engine_misfire"]
        assert validated_ids == [entry_id]

    def test_fuzzy_content_match_accepted(self, db, clean_diagnostic_tables):
        entry_id = uuid.uuid4()
        evidence = [
            KnowledgeSearchResult(
                id=entry_id,
                category="dtc",
                entry_key="P0300",
                content="P0300 indicates random or multiple cylinder misfires.",
                source="test",
                similarity_score=0.85,
            )
        ]

        service = self._make_service(
            DiagnosticHypothesis(
                fault_description="Random misfire",
                confidence_score=0.8,
                severity="medium",
                supporting_evidence=["P0300 indicates random or multiple cylinder misfires"],
                recommended_checks=["Scan DTCs"],
            )
        )
        hypothesis = DiagnosticHypothesis(
            fault_description="Random misfire",
            confidence_score=0.8,
            severity="medium",
            supporting_evidence=["P0300 indicates random or multiple cylinder misfires"],
            recommended_checks=["Scan DTCs"],
        )
        validated_strings, validated_ids = service._validate_evidence(hypothesis, evidence)

        assert len(validated_strings) == 1
        assert validated_ids == [entry_id]

    def test_empty_evidence_returns_empty(self, db, clean_diagnostic_tables):
        service = self._make_service(
            DiagnosticHypothesis(
                fault_description="Faulty spark plugs",
                confidence_score=0.8,
                severity="medium",
                supporting_evidence=["[symptom] engine_misfire"],
                recommended_checks=["Inspect spark plugs"],
            )
        )
        hypothesis = DiagnosticHypothesis(
            fault_description="Faulty spark plugs",
            confidence_score=0.8,
            severity="medium",
            supporting_evidence=["[symptom] engine_misfire"],
            recommended_checks=["Inspect spark plugs"],
        )
        validated_strings, validated_ids = service._validate_evidence(hypothesis, [])

        assert validated_strings == []
        assert validated_ids == []

    def test_malformed_evidence_references_handled(self, db, clean_diagnostic_tables):
        entry_id = uuid.uuid4()
        evidence = [
            KnowledgeSearchResult(
                id=entry_id,
                category="symptom",
                entry_key="engine_misfire",
                content="Engine misfire description",
                source="test",
                similarity_score=0.9,
            )
        ]

        service = self._make_service(
            DiagnosticHypothesis(
                fault_description="Faulty spark plugs",
                confidence_score=0.8,
                severity="medium",
                supporting_evidence=["[symptom] engine_misfire"],
                recommended_checks=["Inspect spark plugs"],
            )
        )
        raw = json.dumps(
            {
                "hypotheses": [
                    {
                        "fault_description": "Faulty spark plugs",
                        "confidence_score": 0.8,
                        "severity": "medium",
                        "supporting_evidence": ["", "   ", "[symptom] engine_misfire", 123],
                        "recommended_checks": ["Inspect spark plugs"],
                    }
                ]
            }
        )
        hypotheses = service._parse_hypotheses(raw)
        assert len(hypotheses) == 1
        validated_strings, validated_ids = service._validate_evidence(hypotheses[0], evidence)

        assert validated_strings == ["[symptom] engine_misfire"]
        assert validated_ids == [entry_id]

    def test_llm_injected_knowledge_references_are_ignored(self, db, clean_diagnostic_tables):
        entry_id = uuid.uuid4()
        hallucinated_id = uuid.uuid4()
        evidence = [
            KnowledgeSearchResult(
                id=entry_id,
                category="symptom",
                entry_key="engine_misfire",
                content="Engine misfire description",
                source="test",
                similarity_score=0.9,
            )
        ]
        service = self._make_service(
            DiagnosticHypothesis(
                fault_description="Faulty spark plugs",
                confidence_score=0.8,
                severity="medium",
                supporting_evidence=["[symptom] engine_misfire"],
                recommended_checks=["Inspect spark plugs"],
            )
        )
        raw = json.dumps(
            {
                "hypotheses": [
                    {
                        "fault_description": "Faulty spark plugs",
                        "confidence_score": 0.8,
                        "severity": "medium",
                        "supporting_evidence": ["[symptom] engine_misfire"],
                        "recommended_checks": ["Inspect spark plugs"],
                        "knowledge_references": [str(hallucinated_id)],
                    }
                ]
            }
        )
        hypotheses = service._parse_hypotheses(raw)
        assert hypotheses[0].knowledge_references == []

        validated_strings, validated_ids = service._validate_evidence(hypotheses[0], evidence)
        assert validated_strings == ["[symptom] engine_misfire"]
        assert validated_ids == [entry_id]
        assert hallucinated_id not in validated_ids


class TestDiagnosticExplainabilityResponse:
    def test_analyze_response_contains_explainability_fields(self, client: TestClient, clean_diagnostic_tables):
        payload = {
            "make": "Toyota",
            "model": "Corolla",
            "year": 2020,
            "symptom_text": "Engine is misfiring",
        }
        response = client.post("/api/v1/diagnostics/analyze", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert "evidence" in data
        assert "hypotheses" in data
        evidence_ids = {item["id"] for item in data["evidence"]}
        for hypothesis in data["hypotheses"]:
            assert "recommended_checks" in hypothesis
            assert "supporting_evidence" in hypothesis
            assert "knowledge_references" in hypothesis
            assert isinstance(hypothesis["knowledge_references"], list)
            for ref in hypothesis["knowledge_references"]:
                assert ref in evidence_ids
