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
    DiagnosticAnalyzeRequest,
    DiagnosticAnalyzeResponse,
    DiagnosticResultCreate,
    DiagnosticResultRead,
    DiagnosticSessionCreate,
    DiagnosticSessionRead,
)
from app.services.diagnostic import DiagnosticService, DiagnosticServiceError, get_diagnostic_service
from app.services.embeddings import EmbeddingService, get_embedding_service
from app.services.llm import LLMService, get_llm_service

router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])


@router.post("/analyze", response_model=DiagnosticAnalyzeResponse, status_code=201)
def analyze_diagnostic(
    request: DiagnosticAnalyzeRequest,
    db: Session = Depends(get_db),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    llm_service: LLMService = Depends(get_llm_service),
) -> DiagnosticAnalyzeResponse:
    diagnostic_service = get_diagnostic_service(embedding_service, llm_service)
    try:
        return diagnostic_service.analyze(db, request)
    except DiagnosticServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


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
