from pathlib import Path

from sqlalchemy.orm import Session

from app.crud import bulk_create_knowledge_entries
from app.schemas import KnowledgeBulkIngestResponse, KnowledgeEntryCreate
from app.services.embeddings import EmbeddingService
from app.services.knowledge_loader import KnowledgeLoader


class KnowledgeIngestionService:
    def __init__(
        self,
        db: Session,
        embedding_service: EmbeddingService,
        loader: KnowledgeLoader | None = None,
    ) -> None:
        self._db = db
        self._embedding_service = embedding_service
        self._loader = loader

    @staticmethod
    def _embedding_text(entry: KnowledgeEntryCreate) -> str:
        return f"{entry.category} {entry.entry_key or ''} {entry.content}".strip()

    def ingest_from_loader(self, skip_existing: bool = True) -> KnowledgeBulkIngestResponse:
        if self._loader is None:
            raise ValueError("KnowledgeLoader is required for file-based ingestion")

        entries = self._loader.load()
        return self.ingest(entries, skip_existing=skip_existing)

    def ingest(
        self, entries: list[KnowledgeEntryCreate], skip_existing: bool = True
    ) -> KnowledgeBulkIngestResponse:
        if not entries:
            return KnowledgeBulkIngestResponse(created=0, skipped=0, errors=[])

        texts = [self._embedding_text(entry) for entry in entries]
        embeddings = self._embedding_service.embed(texts)

        enriched_entries: list[KnowledgeEntryCreate] = []
        for entry, embedding in zip(entries, embeddings):
            data = entry.model_dump()
            data["embedding"] = embedding
            enriched_entries.append(KnowledgeEntryCreate(**data))

        created, skipped, errors = bulk_create_knowledge_entries(
            self._db, enriched_entries, skip_existing=skip_existing
        )
        return KnowledgeBulkIngestResponse(created=created, skipped=skipped, errors=errors)


def get_knowledge_ingestion_service(
    db: Session, embedding_service: EmbeddingService, root_dir: str | Path | None = None
) -> KnowledgeIngestionService:
    loader = None
    if root_dir is not None:
        loader = KnowledgeLoader(root_dir)
    return KnowledgeIngestionService(db, embedding_service, loader)
