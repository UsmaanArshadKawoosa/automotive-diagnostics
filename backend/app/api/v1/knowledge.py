import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.crud import (
    bulk_create_knowledge_entries,
    create_knowledge_entry,
    get_knowledge_entry,
    hybrid_search_knowledge_entries,
    list_knowledge_entries,
    update_knowledge_entry_embedding,
)
from app.db.database import get_db
from app.schemas import (
    KnowledgeBulkIngestRequest,
    KnowledgeBulkIngestResponse,
    KnowledgeEntryCreate,
    KnowledgeEntryRead,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    KnowledgeSearchResult,
)
from app.services.embeddings import EmbeddingService, get_embedding_service
from app.services.knowledge_ingestion import KnowledgeIngestionService

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.post("", response_model=KnowledgeEntryRead, status_code=201)
def create_entry(
    entry_in: KnowledgeEntryCreate,
    db: Session = Depends(get_db),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
) -> KnowledgeEntryRead:
    if entry_in.embedding is None:
        text_to_embed = f"{entry_in.category} {entry_in.entry_key or ''} {entry_in.content}".strip()
        entry_in.embedding = embedding_service.embed_query(text_to_embed)
    return create_knowledge_entry(db, entry_in)


@router.post("/bulk", response_model=KnowledgeBulkIngestResponse, status_code=201)
def create_bulk_entries(
    bulk_in: KnowledgeBulkIngestRequest,
    db: Session = Depends(get_db),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    skip_existing: bool = True,
) -> KnowledgeBulkIngestResponse:
    service = KnowledgeIngestionService(db, embedding_service)
    return service.ingest(bulk_in.entries, skip_existing=skip_existing)


@router.get("", response_model=list[KnowledgeEntryRead])
def read_entries(
    skip: int = 0, limit: int = 100, category: str | None = None, db: Session = Depends(get_db)
) -> list[KnowledgeEntryRead]:
    return list_knowledge_entries(db, skip=skip, limit=limit, category=category)


@router.get("/{entry_id}", response_model=KnowledgeEntryRead)
def read_entry(entry_id: uuid.UUID, db: Session = Depends(get_db)) -> KnowledgeEntryRead:
    entry = get_knowledge_entry(db, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Knowledge entry not found")
    return entry


@router.post("/search", response_model=KnowledgeSearchResponse)
def search_entries(
    search_in: KnowledgeSearchRequest,
    db: Session = Depends(get_db),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
) -> KnowledgeSearchResponse:
    query_embedding = None
    if embedding_service is not None:
        try:
            query_embedding = embedding_service.embed_query(search_in.query)
        except Exception:
            query_embedding = None
    rows = hybrid_search_knowledge_entries(
        db,
        query_embedding=query_embedding,
        query_text=search_in.query,
        category=search_in.category,
        top_k=search_in.top_k,
    )
    results = []
    for entry, score in rows:
        similarity = round(float(score), 4)
        results.append(
            KnowledgeSearchResult(
                id=entry.id,
                category=entry.category,
                entry_key=entry.entry_key,
                content=entry.content,
                source=entry.source,
                similarity_score=similarity,
            )
        )
    return KnowledgeSearchResponse(query=search_in.query, results=results)


@router.post("/{entry_id}/embed", response_model=KnowledgeEntryRead)
def embed_entry(
    entry_id: uuid.UUID,
    db: Session = Depends(get_db),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
) -> KnowledgeEntryRead:
    entry = get_knowledge_entry(db, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Knowledge entry not found")
    text_to_embed = f"{entry.category} {entry.entry_key or ''} {entry.content}".strip()
    embedding = embedding_service.embed_query(text_to_embed)
    updated = update_knowledge_entry_embedding(db, entry_id, embedding)
    if updated is None:
        raise HTTPException(status_code=404, detail="Knowledge entry not found")
    return updated
