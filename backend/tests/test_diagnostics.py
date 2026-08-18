import uuid

import pytest
from fastapi.testclient import TestClient

from app.db.database import engine
from app.schemas import DiagnosticAnalyzeRequest
from app.services.diagnostic import DiagnosticService
from tests.conftest import FakeEmbeddingService, FakeLLMService


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
        assert data["hypotheses"][0]["severity"] in {"low", "medium", "high", "critical"}

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
        assert len(session_response.json()["results"]) >= 1


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
