import json
import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.db.database import engine
from app.schemas import DiagnosticAnalyzeRequest, KnowledgeSearchResult
from app.services.diagnostic import DiagnosticService
from tests.conftest import FakeEmbeddingService, FakeLLMService


class _MockKnowledgeEntry:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class TestDiagnosticAnalyzeRequest:
    def test_symptom_text_required(self):
        with pytest.raises(ValueError):
            DiagnosticAnalyzeRequest(symptom_text="")

    def test_dtc_codes_joined(self):
        request = DiagnosticAnalyzeRequest(
            symptom_text="misfire", dtc_codes=["P0300", "P0301"]
        )
        assert request.dtc_codes_text() == "P0300, P0301"

    def test_no_dtc_codes_returns_none(self):
        request = DiagnosticAnalyzeRequest(symptom_text="misfire")
        assert request.dtc_codes_text() is None

    def test_valid_dtc_codes_accepted_and_normalized(self):
        for code in ("P0300", "p0300", "P0171", "C0033", "B0033", "U0100"):
            request = DiagnosticAnalyzeRequest(symptom_text="misfire", dtc_codes=[code])
            assert request.dtc_codes == [code.upper()]

    def test_invalid_dtc_codes_rejected(self):
        with pytest.raises(ValueError, match="Invalid DTC code"):
            DiagnosticAnalyzeRequest(symptom_text="misfire", dtc_codes=["P030"])
        with pytest.raises(ValueError, match="Invalid DTC code"):
            DiagnosticAnalyzeRequest(symptom_text="misfire", dtc_codes=["P03001"])
        with pytest.raises(ValueError, match="Invalid DTC code"):
            DiagnosticAnalyzeRequest(symptom_text="misfire", dtc_codes=["X0300"])

    def test_empty_dtc_list_rejected(self):
        with pytest.raises(ValueError, match="At least one DTC code"):
            DiagnosticAnalyzeRequest(symptom_text="misfire", dtc_codes=[])

    def test_duplicate_dtc_codes_deduplicated(self):
        request = DiagnosticAnalyzeRequest(symptom_text="misfire", dtc_codes=["P0300", "p0300"])
        assert request.dtc_codes == ["P0300"]

    def test_valid_vin_accepted(self):
        request = DiagnosticAnalyzeRequest(symptom_text="misfire", vin="1HGCM82633A004352")
        assert request.vin == "1HGCM82633A004352"

    def test_invalid_vin_too_short(self):
        with pytest.raises(ValueError, match="VIN must be exactly 17 characters"):
            DiagnosticAnalyzeRequest(symptom_text="misfire", vin="SHORT")

    def test_invalid_vin_contains_forbidden_chars(self):
        for char in ("I", "O", "Q"):
            vin = "1HGCM82633A00435" + char
            with pytest.raises(ValueError, match=f"VIN cannot contain '{char}'"):
                DiagnosticAnalyzeRequest(symptom_text="misfire", vin=vin)

    def test_valid_year_accepted(self):
        request = DiagnosticAnalyzeRequest(symptom_text="misfire", year=2020)
        assert request.year == 2020

    def test_invalid_year_rejected(self):
        with pytest.raises(ValueError):
            DiagnosticAnalyzeRequest(symptom_text="misfire", year=1800)
        with pytest.raises(ValueError):
            DiagnosticAnalyzeRequest(symptom_text="misfire", year=2200)

    def test_symptom_only_request_accepted(self):
        request = DiagnosticAnalyzeRequest(symptom_text="Engine is misfiring")
        assert request.symptom_text == "Engine is misfiring"
        assert request.dtc_codes is None
        assert request.vin is None


class TestDiagnosticService:
    def test_analyze_creates_session_and_results(self, db, clean_diagnostic_tables):
        embedding_service = FakeEmbeddingService()
        llm_service = FakeLLMService()
        service = DiagnosticService(
            app_settings=embedding_service._settings,
            embedding_service=embedding_service,
            llm_service=llm_service,
        )
        request = DiagnosticAnalyzeRequest(
            make="Toyota",
            model="Corolla",
            year=2020,
            dtc_codes=["P0300"],
            symptom_text="Engine is misfiring",
        )
        response = service.analyze(db, request)

        assert response.vehicle["make"] == "Toyota"
        assert response.vehicle["model"] == "Corolla"
        assert response.query != ""
        assert len(response.hypotheses) == 1
        assert response.hypotheses[0].fault_description == "Faulty spark plugs"
        assert response.hypotheses[0].confidence_score == 0.75
        assert isinstance(response.hypotheses[0].recommended_checks, list)
        assert isinstance(response.hypotheses[0].supporting_evidence, list)
        assert isinstance(response.hypotheses[0].knowledge_references, list)

        # Verify persistence
        from sqlalchemy import inspect

        inspector = inspect(engine)
        assert "diagnostic_sessions" in inspector.get_table_names()
        assert "diagnostic_results" in inspector.get_table_names()


class TestDiagnosticAnalyzeEndpoint:
    def test_analyze_endpoint(self, client: TestClient, clean_diagnostic_tables):
        payload = {
            "make": "Toyota",
            "model": "Corolla",
            "year": 2020,
            "dtc_codes": ["P0300"],
            "symptom_text": "Engine is misfiring",
        }
        response = client.post("/api/v1/diagnostics/analyze", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert "session_id" in data
        assert "hypotheses" in data
        assert len(data["hypotheses"]) >= 1
        hypothesis = data["hypotheses"][0]
        assert hypothesis["severity"] in {"low", "medium", "high", "critical"}
        assert "recommended_checks" in hypothesis
        assert "supporting_evidence" in hypothesis
        assert "knowledge_references" in hypothesis
        evidence_ids = {item["id"] for item in data["evidence"]}
        for ref in hypothesis["knowledge_references"]:
            assert ref in evidence_ids

    def test_analyze_persists_results(self, client: TestClient, clean_diagnostic_tables):
        payload = {
            "make": "Toyota",
            "model": "Corolla",
            "year": 2020,
            "symptom_text": "Engine is misfiring",
        }
        response = client.post("/api/v1/diagnostics/analyze", json=payload)
        assert response.status_code == 201
        session_id = response.json()["session_id"]

        session_response = client.get(f"/api/v1/diagnostics/sessions/{session_id}")
        assert session_response.status_code == 200
        data = session_response.json()
        assert len(data["results"]) >= 1
        result = data["results"][0]
        assert result["fault_description"] == "Faulty spark plugs"
        assert result["confidence_score"] == 0.75
        assert result["severity"] == "medium"
        assert result["repair_suggestion"] == "Replace spark plugs if worn"
        assert result["recommended_checks"] == ["Inspect spark plugs"]
        assert isinstance(result["supporting_evidence"], list)
        assert isinstance(result["knowledge_references"], list)
        for ref in result["knowledge_references"]:
            uuid.UUID(ref)


class TestDiagnosticSessionEndpoint:
    def test_create_session(self, client: TestClient, clean_diagnostic_tables):
        payload = {
            "vin": "1HGCM82633A123456",
            "make": "Honda",
            "model": "Accord",
            "year": 2020,
            "symptom_text": "Rough idle",
        }
        response = client.post("/api/v1/diagnostics/sessions", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["make"] == "Honda"
        assert data["results"] == []


class TestDiagnosticRetrievalQuality:
    def test_build_search_query_structures_context(self):
        embedding_service = FakeEmbeddingService()
        llm_service = FakeLLMService()
        service = DiagnosticService(
            app_settings=embedding_service._settings,
            embedding_service=embedding_service,
            llm_service=llm_service,
        )
        request = DiagnosticAnalyzeRequest(
            dtc_codes=["P0300", "P0301"],
            symptom_text="Engine running rough",
            make="Toyota",
            model="Corolla",
            year=2020,
        )
        query = service._build_search_query(request)
        assert query.startswith("DTCs:\nP0300\nP0301")
        assert "Symptoms:\nEngine running rough" in query
        assert "Vehicle:\nToyota Corolla 2020" in query

    def test_symptom_only_query_structure(self):
        embedding_service = FakeEmbeddingService()
        llm_service = FakeLLMService()
        service = DiagnosticService(
            app_settings=embedding_service._settings,
            embedding_service=embedding_service,
            llm_service=llm_service,
        )
        request = DiagnosticAnalyzeRequest(symptom_text="Engine is hesitating")
        query = service._build_search_query(request)
        assert query == "Symptoms:\nEngine is hesitating"

    def test_vehicle_info_does_not_overwhelm_signal(self):
        embedding_service = FakeEmbeddingService()
        llm_service = FakeLLMService()
        service = DiagnosticService(
            app_settings=embedding_service._settings,
            embedding_service=embedding_service,
            llm_service=llm_service,
        )
        request = DiagnosticAnalyzeRequest(
            dtc_codes=["P0300"],
            symptom_text="misfire",
            make="Toyota",
            model="Corolla",
            year=2020,
        )
        query = service._build_search_query(request)
        sections = query.split("\n\n")
        assert sections[0].startswith("DTCs:\nP0300")
        assert "Vehicle" not in sections[0]

    def test_p0300_retrieves_misfire_knowledge(self, db, clean_diagnostic_tables):
        embedding_service = FakeEmbeddingService()
        llm_service = FakeLLMService()
        service = DiagnosticService(
            app_settings=embedding_service._settings,
            embedding_service=embedding_service,
            llm_service=llm_service,
        )
        request = DiagnosticAnalyzeRequest(
            dtc_codes=["P0300"],
            symptom_text="Engine running rough",
        )

        misfire_entry = _MockKnowledgeEntry(
            id=uuid.uuid4(),
            category="dtc",
            entry_key="P0300",
            content="P0300 indicates random or multiple cylinder misfires.",
            source="test",
            embedding=[1.0, 0.0],
        )

        with patch("app.crud.search_knowledge_entries", return_value=[(misfire_entry, 0.1)]):
            response = service.analyze(db, request)

        assert len(response.evidence) == 1
        assert response.evidence[0].entry_key == "P0300"
        assert "misfire" in response.evidence[0].content.lower()
        assert len(response.hypotheses) >= 1
        evidence_ids = {e.id for e in response.evidence}
        for ref in response.hypotheses[0].knowledge_references:
            assert ref in evidence_ids

    def test_p0171_retrieves_lean_knowledge(self, db, clean_diagnostic_tables):
        embedding_service = FakeEmbeddingService()
        llm_service = FakeLLMService()
        service = DiagnosticService(
            app_settings=embedding_service._settings,
            embedding_service=embedding_service,
            llm_service=llm_service,
        )
        request = DiagnosticAnalyzeRequest(
            dtc_codes=["P0171"],
            symptom_text="System too lean, rough idle",
        )

        lean_entry = _MockKnowledgeEntry(
            id=uuid.uuid4(),
            category="dtc",
            entry_key="P0171",
            content="P0171 indicates a lean fuel trim condition.",
            source="test",
            embedding=[1.0, 0.0],
        )

        with patch("app.crud.search_knowledge_entries", return_value=[(lean_entry, 0.1)]):
            response = service.analyze(db, request)

        assert len(response.evidence) == 1
        assert response.evidence[0].entry_key == "P0171"
        assert "lean" in response.evidence[0].content.lower()
        evidence_ids = {e.id for e in response.evidence}
        for ref in response.hypotheses[0].knowledge_references:
            assert ref in evidence_ids

    def test_symptom_only_retrieves_useful_knowledge(self, db, clean_diagnostic_tables):
        embedding_service = FakeEmbeddingService()
        llm_service = FakeLLMService()
        service = DiagnosticService(
            app_settings=embedding_service._settings,
            embedding_service=embedding_service,
            llm_service=llm_service,
        )
        request = DiagnosticAnalyzeRequest(symptom_text="brake pedal feels soft")

        brake_entry = _MockKnowledgeEntry(
            id=uuid.uuid4(),
            category="symptom",
            entry_key="soft_brake_pedal",
            content="Soft brake pedal may indicate air in the brake lines or a failing master cylinder.",
            source="test",
            embedding=[1.0, 0.0],
        )

        with patch("app.crud.search_knowledge_entries", return_value=[(brake_entry, 0.1)]):
            response = service.analyze(db, request)

        assert len(response.evidence) == 1
        assert response.evidence[0].entry_key == "soft_brake_pedal"
        evidence_ids = {e.id for e in response.evidence}
        for ref in response.hypotheses[0].knowledge_references:
            assert ref in evidence_ids

    def test_vehicle_info_does_not_break_retrieval(self, db, clean_diagnostic_tables):
        embedding_service = FakeEmbeddingService()
        llm_service = FakeLLMService()
        service = DiagnosticService(
            app_settings=embedding_service._settings,
            embedding_service=embedding_service,
            llm_service=llm_service,
        )
        request = DiagnosticAnalyzeRequest(
            symptom_text="engine overheating",
            make="Honda",
            model="Civic",
            year=2018,
        )

        overheat_entry = _MockKnowledgeEntry(
            id=uuid.uuid4(),
            category="symptom",
            entry_key="engine_overheating",
            content="Engine overheating can be caused by low coolant, thermostat failure, or water pump issues.",
            source="test",
            embedding=[1.0, 0.0],
        )

        with patch("app.crud.search_knowledge_entries", return_value=[(overheat_entry, 0.1)]):
            response = service.analyze(db, request)

        assert len(response.evidence) == 1
        assert response.evidence[0].entry_key == "engine_overheating"
        evidence_ids = {e.id for e in response.evidence}
        for ref in response.hypotheses[0].knowledge_references:
            assert ref in evidence_ids

    def test_retrieval_results_retain_ids_for_evidence_validation(self, db, clean_diagnostic_tables):
        embedding_service = FakeEmbeddingService()
        llm_service = FakeLLMService()
        service = DiagnosticService(
            app_settings=embedding_service._settings,
            embedding_service=embedding_service,
            llm_service=llm_service,
        )
        request = DiagnosticAnalyzeRequest(
            dtc_codes=["P0300"],
            symptom_text="misfire",
        )

        entry_id = uuid.uuid4()
        misfire_entry = _MockKnowledgeEntry(
            id=entry_id,
            category="dtc",
            entry_key="P0300",
            content="P0300 misfire",
            source="test",
            embedding=[1.0, 0.0],
        )

        with patch("app.crud.search_knowledge_entries", return_value=[(misfire_entry, 0.1)]):
            response = service.analyze(db, request)

        assert entry_id in {e.id for e in response.evidence}
        evidence_ids = {e.id for e in response.evidence}
        for hypothesis in response.hypotheses:
            for ref in hypothesis.knowledge_references:
                assert ref in evidence_ids

    def test_existing_evidence_validation_still_works(self, db, clean_diagnostic_tables):
        embedding_service = FakeEmbeddingService()
        llm_service = FakeLLMService()
        service = DiagnosticService(
            app_settings=embedding_service._settings,
            embedding_service=embedding_service,
            llm_service=llm_service,
        )
        request = DiagnosticAnalyzeRequest(
            dtc_codes=["P0300"],
            symptom_text="misfire",
        )

        entry_id = uuid.uuid4()
        misfire_entry = _MockKnowledgeEntry(
            id=entry_id,
            category="dtc",
            entry_key="P0300",
            content="P0300 misfire",
            source="test",
            embedding=[1.0, 0.0],
        )

        hallucinated_response = json.dumps({
            "hypotheses": [{
                "fault_description": "Faulty spark plugs",
                "confidence_score": 0.8,
                "severity": "medium",
                "supporting_evidence": ["[dtc] P0300", "Made up reference"],
                "recommended_checks": ["Inspect spark plugs"],
            }]
        })
        hallucinated_llm = FakeLLMService(hallucinated_response)
        service = DiagnosticService(
            app_settings=embedding_service._settings,
            embedding_service=embedding_service,
            llm_service=hallucinated_llm,
        )

        with patch("app.crud.search_knowledge_entries", return_value=[(misfire_entry, 0.1)]):
            response = service.analyze(db, request)

        assert len(response.hypotheses) == 1
        assert response.hypotheses[0].supporting_evidence == ["[dtc] P0300"]
        assert response.hypotheses[0].knowledge_references == [entry_id]


class TestDiagnosticAnalyzeEndpointValidation:
    def test_invalid_dtc_returns_422(self, client: TestClient):
        payload = {
            "symptom_text": "misfire",
            "dtc_codes": ["INVALID"],
        }
        response = client.post("/api/v1/diagnostics/analyze", json=payload)
        assert response.status_code == 422

    def test_invalid_vin_returns_422(self, client: TestClient):
        payload = {
            "symptom_text": "misfire",
            "vin": "SHORT",
        }
        response = client.post("/api/v1/diagnostics/analyze", json=payload)
        assert response.status_code == 422

    def test_invalid_year_returns_422(self, client: TestClient):
        payload = {
            "symptom_text": "misfire",
            "year": 1800,
        }
        response = client.post("/api/v1/diagnostics/analyze", json=payload)
        assert response.status_code == 422


class TestSessionHistory:
    def test_new_session_creates_correctly(self, client: TestClient, clean_diagnostic_tables):
        payload = {
            "vin": "1HGCM82633A123456",
            "make": "Honda",
            "model": "Accord",
            "year": 2020,
            "symptom_text": "Rough idle",
            "dtc_codes": "P0300",
        }
        response = client.post("/api/v1/diagnostics/sessions", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["vin"] == "1HGCM82633A123456"
        assert data["make"] == "Honda"
        assert data["results"] == []

    def test_first_result_is_persisted(self, client: TestClient, clean_diagnostic_tables):
        payload = {
            "make": "Toyota",
            "model": "Corolla",
            "year": 2020,
            "dtc_codes": ["P0300"],
            "symptom_text": "Engine misfires at idle",
        }
        response = client.post("/api/v1/diagnostics/analyze", json=payload)
        assert response.status_code == 201
        session_id = response.json()["session_id"]

        session_response = client.get(f"/api/v1/diagnostics/sessions/{session_id}")
        assert session_response.status_code == 200
        data = session_response.json()
        assert len(data["results"]) >= 1
        result = data["results"][0]
        assert result["fault_description"] == "Faulty spark plugs"
        assert result["confidence_score"] == 0.75

    def test_multiple_results_belong_to_one_session(self, client: TestClient, clean_diagnostic_tables):
        payload1 = {
            "make": "Toyota",
            "model": "Corolla",
            "year": 2020,
            "dtc_codes": ["P0300"],
            "symptom_text": "Engine misfires at idle",
        }
        response1 = client.post("/api/v1/diagnostics/analyze", json=payload1)
        assert response1.status_code == 201
        session_id = response1.json()["session_id"]

        payload2 = {
            "make": "Toyota",
            "model": "Corolla",
            "year": 2020,
            "dtc_codes": ["P0300"],
            "symptom_text": "Spark plugs inspected, still misfiring",
        }
        response2 = client.post("/api/v1/diagnostics/sessions/{}/analyze".format(session_id), json=payload2)
        assert response2.status_code == 201

        session_response = client.get(f"/api/v1/diagnostics/sessions/{session_id}")
        assert session_response.status_code == 200
        data = session_response.json()
        assert len(data["results"]) == 2

    def test_session_history_returns_results_chronologically(self, client: TestClient, clean_diagnostic_tables):
        payload = {
            "make": "Toyota",
            "model": "Corolla",
            "year": 2020,
            "dtc_codes": ["P0300"],
            "symptom_text": "Engine misfires at idle",
        }
        response = client.post("/api/v1/diagnostics/analyze", json=payload)
        session_id = response.json()["session_id"]

        session_response = client.get(f"/api/v1/diagnostics/sessions/{session_id}")
        assert session_response.status_code == 200
        data = session_response.json()
        results = data["results"]
        assert len(results) >= 1
        for i in range(len(results) - 1):
            assert results[i]["created_at"] <= results[i + 1]["created_at"]

    def test_follow_up_references_existing_session(self, client: TestClient, clean_diagnostic_tables):
        payload1 = {
            "make": "Toyota",
            "model": "Corolla",
            "year": 2020,
            "dtc_codes": ["P0300"],
            "symptom_text": "Engine misfires at idle",
        }
        response1 = client.post("/api/v1/diagnostics/analyze", json=payload1)
        assert response1.status_code == 201
        session_id = response1.json()["session_id"]

        payload2 = {
            "symptom_text": "The spark plugs look fine, but the engine still shakes at idle",
        }
        response2 = client.post(
            "/api/v1/diagnostics/sessions/{}/analyze".format(session_id), json=payload2
        )
        assert response2.status_code == 201
        data = response2.json()
        assert data["session_id"] == str(session_id)
        assert len(data["hypotheses"]) >= 1
        assert len(data["evidence"]) >= 1

    def test_analyze_with_session_id_field_returns_422(self, client: TestClient, clean_diagnostic_tables):
        payload = {
            "make": "Toyota",
            "model": "Corolla",
            "year": 2020,
            "dtc_codes": ["P0300"],
            "symptom_text": "misfire",
            "session_id": "00000000-0000-0000-0000-000000000000",
        }
        response = client.post("/api/v1/diagnostics/analyze", json=payload)
        assert response.status_code == 422

    def test_nonexistent_session_returns_404(self, client: TestClient, clean_diagnostic_tables):
        fake_id = uuid.uuid4()
        payload = {
            "symptom_text": "misfire",
        }
        response = client.post(
            "/api/v1/diagnostics/sessions/{}/analyze".format(fake_id), json=payload
        )
        assert response.status_code == 404


class TestMultiTurnContext:
    def test_previous_dtcs_in_follow_up_context(self, db, clean_diagnostic_tables):
        embedding_service = FakeEmbeddingService()
        llm_service = FakeLLMService()
        service = DiagnosticService(
            app_settings=embedding_service._settings,
            embedding_service=embedding_service,
            llm_service=llm_service,
        )

        from app.crud import create_diagnostic_session, create_diagnostic_result
        from app.schemas import DiagnosticSessionCreate, DiagnosticResultCreate

        session = create_diagnostic_session(
            db,
            DiagnosticSessionCreate(
                make="Toyota",
                model="Corolla",
                year=2020,
                symptom_text="Engine misfires at idle",
                dtc_codes="P0300",
            ),
        )
        create_diagnostic_result(
            db,
            session.id,
            DiagnosticResultCreate(
                fault_description="Faulty spark plugs",
                confidence_score=0.8,
                severity="medium",
                recommended_checks=["Inspect spark plugs"],
                supporting_evidence=["[dtc] P0300"],
                knowledge_references=[],
            ),
        )

        request = DiagnosticAnalyzeRequest(
            make="Toyota",
            model="Corolla",
            year=2020,
            dtc_codes=["P0300"],
            symptom_text="The spark plugs look fine, but the engine still shakes at idle",
        )
        context = service._build_session_context(session)
        assert "P0300" in context
        assert "Faulty spark plugs" in context
        assert "Inspect spark plugs" in context

    def test_previous_symptoms_in_follow_up_context(self, db, clean_diagnostic_tables):
        embedding_service = FakeEmbeddingService()
        llm_service = FakeLLMService()
        service = DiagnosticService(
            app_settings=embedding_service._settings,
            embedding_service=embedding_service,
            llm_service=llm_service,
        )

        from app.crud import create_diagnostic_session, create_diagnostic_result
        from app.schemas import DiagnosticSessionCreate, DiagnosticResultCreate

        session = create_diagnostic_session(
            db,
            DiagnosticSessionCreate(
                make="Honda",
                model="Civic",
                year=2018,
                symptom_text="Engine overheating after long drive",
                dtc_codes=None,
            ),
        )
        create_diagnostic_result(
            db,
            session.id,
            DiagnosticResultCreate(
                fault_description="Thermostat failure",
                confidence_score=0.7,
                severity="high",
                recommended_checks=["Check coolant flow", "Test thermostat"],
                supporting_evidence=["[symptom] engine_overheating"],
                knowledge_references=[],
            ),
        )

        request = DiagnosticAnalyzeRequest(
            make="Honda",
            model="Civic",
            year=2018,
            symptom_text="Coolant level is normal, but temperature gauge still rises",
        )
        context = service._build_session_context(session)
        assert "Engine overheating after long drive"[:100] in context
        assert "Thermostat failure" in context

    def test_current_symptoms_not_replaced_by_history(self, db, clean_diagnostic_tables):
        embedding_service = FakeEmbeddingService()
        llm_service = FakeLLMService()
        service = DiagnosticService(
            app_settings=embedding_service._settings,
            embedding_service=embedding_service,
            llm_service=llm_service,
        )

        from app.crud import create_diagnostic_session, create_diagnostic_result
        from app.schemas import DiagnosticSessionCreate, DiagnosticResultCreate

        session = create_diagnostic_session(
            db,
            DiagnosticSessionCreate(
                make="Toyota",
                model="Corolla",
                year=2020,
                symptom_text="Engine misfires at idle",
                dtc_codes="P0300",
            ),
        )
        create_diagnostic_result(
            db,
            session.id,
            DiagnosticResultCreate(
                fault_description="Faulty spark plugs",
                confidence_score=0.8,
                severity="medium",
                recommended_checks=["Inspect spark plugs"],
                supporting_evidence=["[dtc] P0300"],
                knowledge_references=[],
            ),
        )

        request = DiagnosticAnalyzeRequest(
            make="Toyota",
            model="Corolla",
            year=2020,
            dtc_codes=["P0300"],
            symptom_text="The spark plugs look fine, but the engine still shakes at idle",
        )
        query = service._build_search_query(request)
        assert "shakes at idle" in query
        assert "P0300" in query

    def test_historical_context_passed_to_llm(self, db, clean_diagnostic_tables):
        embedding_service = FakeEmbeddingService()
        llm_service = FakeLLMService()
        service = DiagnosticService(
            app_settings=embedding_service._settings,
            embedding_service=embedding_service,
            llm_service=llm_service,
        )

        from app.crud import create_diagnostic_session, create_diagnostic_result
        from app.schemas import DiagnosticSessionCreate, DiagnosticResultCreate

        session = create_diagnostic_session(
            db,
            DiagnosticSessionCreate(
                make="Toyota",
                model="Corolla",
                year=2020,
                symptom_text="Engine misfires at idle",
                dtc_codes="P0300",
            ),
        )
        create_diagnostic_result(
            db,
            session.id,
            DiagnosticResultCreate(
                fault_description="Faulty spark plugs",
                confidence_score=0.8,
                severity="medium",
                recommended_checks=["Inspect spark plugs"],
                supporting_evidence=["[dtc] P0300"],
                knowledge_references=[],
            ),
        )

        request = DiagnosticAnalyzeRequest(
            make="Toyota",
            model="Corolla",
            year=2020,
            dtc_codes=["P0300"],
            symptom_text="The spark plugs look fine, but the engine still shakes at idle",
        )
        evidence = []
        prompt = service._build_prompt(request, evidence, session_context="Previous turn: P0300 misfire")
        assert "PREVIOUS SESSION CONTEXT" in prompt
        assert "P0300 misfire" in prompt
        assert "Current symptoms" in prompt or "Symptoms:" in prompt

    def test_multi_turn_evidence_validation_works(self, client: TestClient, clean_diagnostic_tables):
        from app.services.diagnostic import DiagnosticService

        embedding_service = FakeEmbeddingService()
        llm_service = FakeLLMService()
        service = DiagnosticService(
            app_settings=embedding_service._settings,
            embedding_service=embedding_service,
            llm_service=llm_service,
        )

        payload1 = {
            "make": "Toyota",
            "model": "Corolla",
            "year": 2020,
            "dtc_codes": ["P0300"],
            "symptom_text": "Engine misfires at idle",
        }
        response1 = client.post("/api/v1/diagnostics/analyze", json=payload1)
        assert response1.status_code == 201
        session_id = response1.json()["session_id"]

        payload2 = {
            "symptom_text": "The spark plugs look fine, but the engine still shakes at idle",
        }
        response2 = client.post(
            "/api/v1/diagnostics/sessions/{}/analyze".format(session_id), json=payload2
        )
        assert response2.status_code == 201
        data = response2.json()
        assert len(data["hypotheses"]) >= 1
        evidence_ids = {item["id"] for item in data["evidence"]}
        for ref in data["hypotheses"][0]["knowledge_references"]:
            assert ref in evidence_ids

    def test_single_turn_behavior_unchanged(self, client: TestClient, clean_diagnostic_tables):
        payload = {
            "make": "Toyota",
            "model": "Corolla",
            "year": 2020,
            "dtc_codes": ["P0300"],
            "symptom_text": "Engine is misfiring",
        }
        response = client.post("/api/v1/diagnostics/analyze", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert "session_id" in data
        assert "hypotheses" in data
        assert len(data["hypotheses"]) >= 1
        assert data["hypotheses"][0]["fault_description"] == "Faulty spark plugs"


class TestHypothesisOutcomeTracking:
    def test_new_hypotheses_default_to_proposed(self, client: TestClient, clean_diagnostic_tables):
        payload = {
            "make": "Toyota",
            "model": "Corolla",
            "year": 2020,
            "dtc_codes": ["P0300"],
            "symptom_text": "Engine misfires at idle",
        }
        response = client.post("/api/v1/diagnostics/analyze", json=payload)
        assert response.status_code == 201
        session_id = response.json()["session_id"]

        session_response = client.get(f"/api/v1/diagnostics/sessions/{session_id}")
        assert session_response.status_code == 200
        data = session_response.json()
        assert len(data["results"]) >= 1
        result = data["results"][0]
        assert result["hypothesis_status"] == "proposed"

    def test_hypothesis_can_be_marked_investigating(self, client: TestClient, clean_diagnostic_tables):
        payload = {
            "make": "Toyota",
            "model": "Corolla",
            "year": 2020,
            "dtc_codes": ["P0300"],
            "symptom_text": "Engine misfires at idle",
        }
        response = client.post("/api/v1/diagnostics/analyze", json=payload)
        session_id = response.json()["session_id"]

        session_response = client.get(f"/api/v1/diagnostics/sessions/{session_id}")
        result_id = session_response.json()["results"][0]["id"]

        update_payload = {"hypothesis_status": "investigating", "observed_result": "Checking ignition coils"}
        update_response = client.patch(f"/api/v1/diagnostics/results/{result_id}/outcome", json=update_payload)
        assert update_response.status_code == 200
        assert update_response.json()["hypothesis_status"] == "investigating"
        assert update_response.json()["observed_result"] == "Checking ignition coils"

    def test_hypothesis_can_be_confirmed(self, client: TestClient, clean_diagnostic_tables):
        payload = {
            "make": "Toyota",
            "model": "Corolla",
            "year": 2020,
            "dtc_codes": ["P0300"],
            "symptom_text": "Engine misfires at idle",
        }
        response = client.post("/api/v1/diagnostics/analyze", json=payload)
        session_id = response.json()["session_id"]

        session_response = client.get(f"/api/v1/diagnostics/sessions/{session_id}")
        result_id = session_response.json()["results"][0]["id"]

        update_payload = {"hypothesis_status": "confirmed", "observed_result": "Faulty coil confirmed"}
        update_response = client.patch(f"/api/v1/diagnostics/results/{result_id}/outcome", json=update_payload)
        assert update_response.status_code == 200
        assert update_response.json()["hypothesis_status"] == "confirmed"

    def test_hypothesis_can_be_rejected(self, client: TestClient, clean_diagnostic_tables):
        payload = {
            "make": "Toyota",
            "model": "Corolla",
            "year": 2020,
            "dtc_codes": ["P0300"],
            "symptom_text": "Engine misfires at idle",
        }
        response = client.post("/api/v1/diagnostics/analyze", json=payload)
        session_id = response.json()["session_id"]

        session_response = client.get(f"/api/v1/diagnostics/sessions/{session_id}")
        result_id = session_response.json()["results"][0]["id"]

        update_payload = {"hypothesis_status": "rejected", "observed_result": "Spark plugs are fine"}
        update_response = client.patch(f"/api/v1/diagnostics/results/{result_id}/outcome", json=update_payload)
        assert update_response.status_code == 200
        assert update_response.json()["hypothesis_status"] == "rejected"

    def test_invalid_status_rejected(self, client: TestClient, clean_diagnostic_tables):
        payload = {
            "make": "Toyota",
            "model": "Corolla",
            "year": 2020,
            "dtc_codes": ["P0300"],
            "symptom_text": "Engine misfires at idle",
        }
        response = client.post("/api/v1/diagnostics/analyze", json=payload)
        session_id = response.json()["session_id"]

        session_response = client.get(f"/api/v1/diagnostics/sessions/{session_id}")
        result_id = session_response.json()["results"][0]["id"]

        update_payload = {"hypothesis_status": "invalid_status"}
        update_response = client.patch(f"/api/v1/diagnostics/results/{result_id}/outcome", json=update_payload)
        assert update_response.status_code == 422

    def test_recommended_check_can_be_marked_performed(self, client: TestClient, clean_diagnostic_tables):
        payload = {
            "make": "Toyota",
            "model": "Corolla",
            "year": 2020,
            "dtc_codes": ["P0300"],
            "symptom_text": "Engine misfires at idle",
        }
        response = client.post("/api/v1/diagnostics/analyze", json=payload)
        session_id = response.json()["session_id"]

        session_response = client.get(f"/api/v1/diagnostics/sessions/{session_id}")
        result_id = session_response.json()["results"][0]["id"]

        check_payload = {
            "check_description": "Inspect spark plugs",
            "status": "performed",
            "observed_result": "Spark plugs worn",
            "technician_note": "Replace needed",
        }
        check_response = client.post(f"/api/v1/diagnostics/results/{result_id}/checks", json=check_payload)
        assert check_response.status_code == 201
        assert check_response.json()["status"] == "performed"
        assert check_response.json()["observed_result"] == "Spark plugs worn"

    def test_check_can_be_marked_passed(self, client: TestClient, clean_diagnostic_tables):
        payload = {
            "make": "Toyota",
            "model": "Corolla",
            "year": 2020,
            "dtc_codes": ["P0300"],
            "symptom_text": "Engine misfires at idle",
        }
        response = client.post("/api/v1/diagnostics/analyze", json=payload)
        session_id = response.json()["session_id"]

        session_response = client.get(f"/api/v1/diagnostics/sessions/{session_id}")
        result_id = session_response.json()["results"][0]["id"]

        check_payload = {
            "check_description": "Check fuel pressure",
            "status": "performed",
        }
        check_response = client.post(f"/api/v1/diagnostics/results/{result_id}/checks", json=check_payload)
        outcome_id = check_response.json()["id"]

        update_payload = {"status": "passed"}
        update_response = client.patch(f"/api/v1/diagnostics/checks/{outcome_id}", json=update_payload)
        assert update_response.status_code == 200
        assert update_response.json()["status"] == "passed"

    def test_check_can_be_marked_failed(self, client: TestClient, clean_diagnostic_tables):
        payload = {
            "make": "Toyota",
            "model": "Corolla",
            "year": 2020,
            "dtc_codes": ["P0300"],
            "symptom_text": "Engine misfires at idle",
        }
        response = client.post("/api/v1/diagnostics/analyze", json=payload)
        session_id = response.json()["session_id"]

        session_response = client.get(f"/api/v1/diagnostics/sessions/{session_id}")
        result_id = session_response.json()["results"][0]["id"]

        check_payload = {
            "check_description": "Test compression",
            "status": "performed",
        }
        check_response = client.post(f"/api/v1/diagnostics/results/{result_id}/checks", json=check_payload)
        outcome_id = check_response.json()["id"]

        update_payload = {"status": "failed"}
        update_response = client.patch(f"/api/v1/diagnostics/checks/{outcome_id}", json=update_payload)
        assert update_response.status_code == 200
        assert update_response.json()["status"] == "failed"

    def test_session_history_exposes_outcomes(self, client: TestClient, clean_diagnostic_tables):
        payload = {
            "make": "Toyota",
            "model": "Corolla",
            "year": 2020,
            "dtc_codes": ["P0300"],
            "symptom_text": "Engine misfires at idle",
        }
        response = client.post("/api/v1/diagnostics/analyze", json=payload)
        session_id = response.json()["session_id"]

        session_response = client.get(f"/api/v1/diagnostics/sessions/{session_id}")
        result_id = session_response.json()["results"][0]["id"]

        client.patch(
            f"/api/v1/diagnostics/results/{result_id}/outcome",
            json={"hypothesis_status": "confirmed", "observed_result": "Coil replaced, misfire gone"},
        )

        session_response = client.get(f"/api/v1/diagnostics/sessions/{session_id}")
        result = session_response.json()["results"][0]
        assert result["hypothesis_status"] == "confirmed"
        assert result["observed_result"] == "Coil replaced, misfire gone"

    def test_confirmed_hypothesis_in_multi_turn_context(self, db, clean_diagnostic_tables):
        embedding_service = FakeEmbeddingService()
        llm_service = FakeLLMService()
        service = DiagnosticService(
            app_settings=embedding_service._settings,
            embedding_service=embedding_service,
            llm_service=llm_service,
        )

        from app.crud import create_diagnostic_session, create_diagnostic_result
        from app.schemas import DiagnosticSessionCreate, DiagnosticResultCreate

        session = create_diagnostic_session(
            db,
            DiagnosticSessionCreate(
                make="Toyota",
                model="Corolla",
                year=2020,
                symptom_text="Engine misfires at idle",
                dtc_codes="P0300",
            ),
        )
        create_diagnostic_result(
            db,
            session.id,
            DiagnosticResultCreate(
                fault_description="Faulty ignition coil",
                confidence_score=0.9,
                severity="high",
                hypothesis_status="confirmed",
                observed_result="Coil replaced, misfire resolved",
                recommended_checks=["Test ignition coil resistance"],
                supporting_evidence=["[dtc] P0300"],
                knowledge_references=[],
            ),
        )

        context = service._build_session_context(session)
        assert "CONFIRMED HYPOTHESES" in context
        assert "Faulty ignition coil" in context
        assert "Coil replaced, misfire resolved" in context

    def test_rejected_hypothesis_clearly_marked_in_context(self, db, clean_diagnostic_tables):
        embedding_service = FakeEmbeddingService()
        llm_service = FakeLLMService()
        service = DiagnosticService(
            app_settings=embedding_service._settings,
            embedding_service=embedding_service,
            llm_service=llm_service,
        )

        from app.crud import create_diagnostic_session, create_diagnostic_result
        from app.schemas import DiagnosticSessionCreate, DiagnosticResultCreate

        session = create_diagnostic_session(
            db,
            DiagnosticSessionCreate(
                make="Toyota",
                model="Corolla",
                year=2020,
                symptom_text="Engine misfires at idle",
                dtc_codes="P0300",
            ),
        )
        create_diagnostic_result(
            db,
            session.id,
            DiagnosticResultCreate(
                fault_description="Vacuum leak",
                confidence_score=0.5,
                severity="medium",
                hypothesis_status="rejected",
                observed_result="No vacuum leak found",
                recommended_checks=["Smoke test intake"],
                supporting_evidence=["[symptom] rough_idle"],
                knowledge_references=[],
            ),
        )

        context = service._build_session_context(session)
        assert "REJECTED HYPOTHESES" in context
        assert "Vacuum leak" in context
        assert "No vacuum leak found" in context

    def test_rejected_hypothesis_not_active_evidence(self, client: TestClient, db, clean_diagnostic_tables):
        embedding_service = FakeEmbeddingService()
        llm_service = FakeLLMService()
        service = DiagnosticService(
            app_settings=embedding_service._settings,
            embedding_service=embedding_service,
            llm_service=llm_service,
        )

        from app.crud import create_diagnostic_session, create_diagnostic_result
        from app.schemas import DiagnosticSessionCreate, DiagnosticResultCreate

        session = create_diagnostic_session(
            db,
            DiagnosticSessionCreate(
                make="Toyota",
                model="Corolla",
                year=2020,
                symptom_text="Engine misfires at idle",
                dtc_codes="P0300",
            ),
        )
        create_diagnostic_result(
            db,
            session.id,
            DiagnosticResultCreate(
                fault_description="Vacuum leak",
                confidence_score=0.5,
                severity="medium",
                hypothesis_status="rejected",
                observed_result="No vacuum leak found",
                recommended_checks=["Smoke test intake"],
                supporting_evidence=["[symptom] rough_idle"],
                knowledge_references=[],
            ),
        )

        request = DiagnosticAnalyzeRequest(
            make="Toyota",
            model="Corolla",
            year=2020,
            dtc_codes=["P0300"],
            symptom_text="Still misfiring after smoke test",
        )
        context = service._build_session_context(session)
        assert "REJECTED HYPOTHESES (do not treat as active causes)" in context

    def test_evidence_validation_remains_intact(self, client: TestClient, clean_diagnostic_tables):
        from app.services.diagnostic import DiagnosticService

        embedding_service = FakeEmbeddingService()
        llm_service = FakeLLMService()
        service = DiagnosticService(
            app_settings=embedding_service._settings,
            embedding_service=embedding_service,
            llm_service=llm_service,
        )

        payload1 = {
            "make": "Toyota",
            "model": "Corolla",
            "year": 2020,
            "dtc_codes": ["P0300"],
            "symptom_text": "Engine misfires at idle",
        }
        response1 = client.post("/api/v1/diagnostics/analyze", json=payload1)
        assert response1.status_code == 201
        session_id = response1.json()["session_id"]

        session_response = client.get(f"/api/v1/diagnostics/sessions/{session_id}")
        result_id = session_response.json()["results"][0]["id"]

        client.patch(
            f"/api/v1/diagnostics/results/{result_id}/outcome",
            json={"hypothesis_status": "investigating"},
        )

        payload2 = {
            "symptom_text": "The spark plugs look fine, but the engine still shakes at idle",
        }
        response2 = client.post(
            "/api/v1/diagnostics/sessions/{}/analyze".format(session_id), json=payload2
        )
        assert response2.status_code == 201
        data = response2.json()
        assert len(data["hypotheses"]) >= 1
        evidence_ids = {item["id"] for item in data["evidence"]}
        for ref in data["hypotheses"][0]["knowledge_references"]:
            assert ref in evidence_ids

    def test_single_turn_behavior_unchanged_by_outcomes(self, client: TestClient, clean_diagnostic_tables):
        payload = {
            "make": "Toyota",
            "model": "Corolla",
            "year": 2020,
            "dtc_codes": ["P0300"],
            "symptom_text": "Engine is misfiring",
        }
        response = client.post("/api/v1/diagnostics/analyze", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert "session_id" in data
        assert "hypotheses" in data
        assert len(data["hypotheses"]) >= 1
        assert data["hypotheses"][0]["fault_description"] == "Faulty spark plugs"
        assert data["hypotheses"][0].get("knowledge_references") is not None
