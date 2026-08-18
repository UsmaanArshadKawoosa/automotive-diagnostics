import uuid

from sqlalchemy.orm import Session

from app.db import models
from app.schemas import DiagnosticSessionCreate, DiagnosticResultCreate, KnowledgeEntryCreate


def create_diagnostic_session(db: Session, session_in: DiagnosticSessionCreate) -> models.DiagnosticSession:
    session = models.DiagnosticSession(**session_in.model_dump())
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_diagnostic_session(db: Session, session_id: uuid.UUID) -> models.DiagnosticSession | None:
    return db.get(models.DiagnosticSession, session_id)


def list_diagnostic_sessions(db: Session, skip: int = 0, limit: int = 100) -> list[models.DiagnosticSession]:
    return db.query(models.DiagnosticSession).offset(skip).limit(limit).all()


def create_diagnostic_result(
    db: Session, session_id: uuid.UUID, result_in: DiagnosticResultCreate
) -> models.DiagnosticResult:
    result = models.DiagnosticResult(session_id=session_id, **result_in.model_dump())
    db.add(result)
    db.commit()
    db.refresh(result)
    return result


def create_knowledge_entry(db: Session, entry_in: KnowledgeEntryCreate) -> models.KnowledgeEntry:
    entry = models.KnowledgeEntry(**entry_in.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def get_knowledge_entry(db: Session, entry_id: uuid.UUID) -> models.KnowledgeEntry | None:
    return db.get(models.KnowledgeEntry, entry_id)


def list_knowledge_entries(
    db: Session, skip: int = 0, limit: int = 100, category: str | None = None
) -> list[models.KnowledgeEntry]:
    query = db.query(models.KnowledgeEntry)
    if category:
        query = query.filter(models.KnowledgeEntry.category == category)
    return query.offset(skip).limit(limit).all()
