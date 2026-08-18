from abc import ABC, abstractmethod
from typing import ClassVar

from app.config import Settings, settings


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return a list of embedding vectors for the input texts."""


class SentenceTransformersProvider(EmbeddingProvider):
    _instance: ClassVar["SentenceTransformersProvider | None"] = None
    _model: ClassVar[object | None] = None

    def __new__(cls, model_name: str) -> "SentenceTransformersProvider":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._model_name = model_name
        return cls._instance

    @property
    def model(self) -> object:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._model_name)
        return self._model

    def embed(self, texts: list[str]) -> list[list[float]]:
        embeddings = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        return embeddings.tolist()


class OpenAIProvider(EmbeddingProvider):
    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model
        self._client: object | None = None

    @property
    def client(self) -> object:
        if self._client is None:
            import openai

            self._client = openai.OpenAI(api_key=self._api_key)
        return self._client

    def embed(self, texts: list[str]) -> list[list[float]]:
        response = self.client.embeddings.create(input=texts, model=self._model)
        return [item.embedding for item in response.data]


class EmbeddingService:
    def __init__(self, app_settings: Settings) -> None:
        self._settings = app_settings
        self._provider = self._build_provider()

    def _build_provider(self) -> EmbeddingProvider:
        provider = self._settings.embedding_provider.lower()
        if provider == "openai":
            if not self._settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY is required when embedding_provider=openai")
            return OpenAIProvider(
                api_key=self._settings.openai_api_key,
                model=self._settings.openai_embedding_model,
            )
        if provider == "sentence-transformers":
            return SentenceTransformersProvider(model_name=self._settings.embedding_model)
        raise ValueError(f"Unsupported embedding provider: {self._settings.embedding_provider}")

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return self._provider.embed(texts)

    def embed_query(self, text: str) -> list[float]:
        return self.embed([text])[0]


def get_embedding_service() -> EmbeddingService:
    return EmbeddingService(settings)
