"""
Deterministic Embedding Service for evaluation.

Generates embeddings based on text content to enable meaningful retrieval
without requiring a live embedding model.
"""
import hashlib
from typing import Any

from app.config import Settings, settings
from app.services.embeddings import EmbeddingService


class DeterministicEmbeddingService(EmbeddingService):
    """Embedding service that generates deterministic embeddings from text content.

    Uses keyword-based hashing to create embeddings where similar texts
    (e.g., same DTC codes, similar symptoms) get similar embeddings.
    """

    def __init__(self) -> None:
        self._settings = Settings()
        self._dim = 384

    def _text_to_embedding(self, text: str) -> list[float]:
        """Convert text to a deterministic embedding vector."""
        text_lower = text.lower()
        embedding = [0.0] * self._dim

        # DTC codes - map to specific dimensions
        import re
        dtc_codes = re.findall(r'\b[PCBU]\d{4}\b', text_lower)
        for i, dtc in enumerate(dtc_codes):
            # Hash DTC to a dimension index
            idx = int(hashlib.md5(dtc.encode()).hexdigest(), 16) % self._dim
            embedding[idx] = 1.0

        # Symptom keywords - map to dimensions
        symptom_keywords = [
            "misfire", "rough idle", "lean", "overheat", "soft brake",
            "hard start", "crank", "no start", "stall", "idle",
            "acceleration", "power", "fuel", "check engine",
            "vacuum", "thermostat", "coolant", "evap", "purge",
            "vent", "alternator", "speed sensor", "brake booster",
            "injector", "coil", "spark plug", "maf", "map",
            "oxygen sensor", "knock", "crankshaft", "camshaft",
        ]
        for i, kw in enumerate(symptom_keywords):
            if kw in text_lower:
                idx = (i * 7) % self._dim  # Spread across dimensions
                embedding[idx] = 0.8

        # Vehicle info
        for i, kw in enumerate(["toyota", "honda", "ford", "chevrolet", "nissan"]):
            if kw in text_lower:
                idx = (100 + i * 3) % self._dim
                embedding[idx] = 0.5

        # If no features matched, use hash of full text
        if all(v == 0.0 for v in embedding):
            hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
            for i in range(self._dim):
                embedding[i] = ((hash_val >> (i % 32)) & 1) * 0.1

        # Normalize
        norm = sum(v * v for v in embedding) ** 0.5
        if norm > 0:
            embedding = [v / norm for v in embedding]

        return embedding

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._text_to_embedding(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._text_to_embedding(text)