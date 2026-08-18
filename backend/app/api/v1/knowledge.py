import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.crud import create_knowledge_entry, get_knowledge_entry, list_knowledge_entries
from app.db.database import get_db
from app.schemas import KnowledgeEntryCreate, KnowledgeEntryRead

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.post("", response_model=KnowledgeEntryRead, status_code=201)
def create_entry(entry_in: KnowledgeEntryCreate, db: Session = Depends(get_db)) -> KnowledgeEntryRead:
    return create_knowledge_entry(db, entry_in)


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
