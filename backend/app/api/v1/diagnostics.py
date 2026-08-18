import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.crud import (
    create_diagnostic_result,
    create_diagnostic_session,
    get_diagnostic_session,
    list_diagnostic_sessions,
)
from app.db.database import get_db
from app.schemas import (
    DiagnosticResultCreate,
    DiagnosticResultRead,
    DiagnosticSessionCreate,
    DiagnosticSessionRead,
)

router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])


@router.post("/sessions", response_model=DiagnosticSessionRead, status_code=201)
def create_session(session_in: DiagnosticSessionCreate, db: Session = Depends(get_db)) -> DiagnosticSessionRead:
    return create_diagnostic_session(db, session_in)


@router.get("/sessions", response_model=list[DiagnosticSessionRead])
def read_sessions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)) -> list[DiagnosticSessionRead]:
    return list_diagnostic_sessions(db, skip=skip, limit=limit)


@router.get("/sessions/{session_id}", response_model=DiagnosticSessionRead)
def read_session(session_id: uuid.UUID, db: Session = Depends(get_db)) -> DiagnosticSessionRead:
    session = get_diagnostic_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Diagnostic session not found")
    return session


@router.post("/sessions/{session_id}/results", response_model=DiagnosticResultRead, status_code=201)
def create_result(
    session_id: uuid.UUID, result_in: DiagnosticResultCreate, db: Session = Depends(get_db)
) -> DiagnosticResultRead:
    session = get_diagnostic_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Diagnostic session not found")
    return create_diagnostic_result(db, session_id, result_in)
