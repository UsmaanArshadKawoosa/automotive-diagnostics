import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app
from app.services.diagnostic import DiagnosticServiceError
from app.services.llm import LLMProviderError, LLMService


class TestHealthEndpoints:
    def test_health_returns_healthy(self, client: TestClient):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_ready_returns_ready(self, client: TestClient):
        response = client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"


class TestProductionErrorSanitization:
    def test_diagnostic_service_error_sanitized_in_production(self, client: TestClient):
        with patch("app.config.settings.debug", False):
            response = client.get("/api/diagnostics/sessions/00000000-0000-0000-0000-000000000000")
            assert response.status_code == 404
            data = response.json()
            assert "detail" in data

    def test_llm_provider_error_sanitized_in_production(self, client: TestClient):
        from app.services.llm import get_llm_service

        class FailingLLMService(LLMService):
            def __init__(self):
                pass

            def complete(self, prompt, response_schema=None):
                raise LLMProviderError("Cannot connect to Ollama at http://localhost:11434")

        with patch("app.config.settings.debug", False):
            app.dependency_overrides[get_llm_service] = lambda: FailingLLMService()
            try:
                response = client.post(
                    "/api/v1/diagnostics/analyze",
                    json={"symptom_text": "test"},
                )
                assert response.status_code == 503
                data = response.json()
                assert "Ollama" not in data["detail"]
                assert "localhost" not in data["detail"]
            finally:
                app.dependency_overrides.pop(get_llm_service, None)


class TestConfigDefaults:
    def test_debug_defaults_to_true_in_development(self):
        with patch.dict(os.environ, {"APP_ENV": "development"}, clear=False):
            settings = Settings()
            assert settings.debug is True

    def test_cors_origins_parsed_correctly(self):
        with patch.dict(os.environ, {"CORS_ORIGINS": "https://example.com,https://app.example.com"}, clear=False):
            settings = Settings()
            assert settings.cors_origins == "https://example.com,https://app.example.com"
