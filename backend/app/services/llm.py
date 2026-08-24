import json
from abc import ABC, abstractmethod
from typing import Any

import httpx

from app.config import Settings, settings


class LLMProviderError(Exception):
    pass


class LLMProvider(ABC):
    @abstractmethod
    def complete(self, prompt: str, response_schema: dict[str, Any] | None = None) -> str:
        """Send a prompt to the LLM and return the raw text response."""


class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str, model: str, temperature: float = 0.2, max_tokens: int = 2048) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._client: httpx.Client | None = None

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(base_url=self._base_url, timeout=120.0)
        return self._client

    def complete(self, prompt: str, response_schema: dict[str, Any] | None = None) -> str:
        payload: dict[str, Any] = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self._temperature,
                "num_predict": self._max_tokens,
            },
        }
        if response_schema is not None:
            payload["format"] = response_schema

        try:
            response = self.client.post("/api/generate", json=payload)
        except httpx.ConnectError as exc:
            raise LLMProviderError(
                f"Cannot connect to Ollama at {self._base_url}. "
                "Ensure Ollama is running or set a different LLM provider."
            ) from exc

        if response.status_code != 200:
            raise LLMProviderError(
                f"Ollama returned HTTP {response.status_code}: {response.text}"
            )

        data = response.json()
        return data.get("response", "")


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str, temperature: float = 0.2, max_tokens: int = 2048, base_url: str | None = None) -> None:
        self._api_key = api_key
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._base_url = base_url
        self._client: Any | None = None

    @property
    def client(self) -> Any:
        if self._client is None:
            import openai

            kwargs: dict[str, Any] = {"api_key": self._api_key}
            if self._base_url:
                kwargs["base_url"] = self._base_url
            self._client = openai.OpenAI(**kwargs)
        return self._client

    def complete(self, prompt: str, response_schema: dict[str, Any] | None = None) -> str:
        messages = [{"role": "user", "content": prompt}]
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
        }
        
        if response_schema is not None:
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "diagnostic_response",
                    "schema": response_schema,
                    "strict": True,
                },
            }

        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""


class LLMService:
    def __init__(self, app_settings: Settings) -> None:
        self._settings = app_settings
        self._provider = self._build_provider()

    def _build_provider(self) -> LLMProvider:
        provider = self._settings.llm_provider.lower()
        if provider == "ollama":
            return OllamaProvider(
                base_url=self._settings.llm_base_url,
                model=self._settings.llm_model,
                temperature=self._settings.llm_temperature,
                max_tokens=self._settings.llm_max_tokens,
            )
        if provider == "openai":
            if not self._settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY is required when llm_provider=openai")
            return OpenAIProvider(
                api_key=self._settings.openai_api_key,
                model=self._settings.llm_model,
                temperature=self._settings.llm_temperature,
                max_tokens=self._settings.llm_max_tokens,
                base_url=self._settings.llm_base_url or None,
            )
        raise ValueError(f"Unsupported LLM provider: {self._settings.llm_provider}")

    def complete(self, prompt: str, response_schema: dict[str, Any] | None = None) -> str:
        return self._provider.complete(prompt, response_schema)


def get_llm_service() -> LLMService:
    return LLMService(settings)
