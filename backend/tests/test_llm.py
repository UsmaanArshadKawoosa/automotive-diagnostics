import json
from typing import Any

import pytest

from app.services.llm import LLMProviderError, LLMService
from tests.conftest import FakeLLMProvider


class TestLLMProviderAbstraction:
    def test_fake_provider_returns_configured_response(self):
        provider = FakeLLMProvider('{"hypotheses": []}')
        assert provider.complete("test") == '{"hypotheses": []}'

    def test_llm_service_uses_provider(self):
        service = LLMService.__new__(LLMService)
        service._provider = FakeLLMProvider('{"answer": 42}')
        assert service.complete("test") == '{"answer": 42}'


class TestLLMProviderConfiguration:
    def test_unsupported_provider_raises(self):
        from app.config import Settings

        settings = Settings(llm_provider="unknown")
        with pytest.raises(ValueError, match="Unsupported LLM provider"):
            LLMService(settings)

    def test_openai_without_key_raises(self):
        from app.config import Settings

        settings = Settings(llm_provider="openai", openai_api_key=None)
        with pytest.raises(ValueError, match="OPENAI_API_KEY is required"):
            LLMService(settings)
