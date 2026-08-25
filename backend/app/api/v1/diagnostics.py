import uuid

from fastapi import APIRouter, Depends, HTTPException
from starlette.responses import JSONResponse
from sqlalchemy.orm import Session

from app.crud import (
    create_check_outcome,
    create_confirmed_case,
    create_diagnostic_result,
    create_diagnostic_session,
    get_check_outcome,
    get_confirmed_case_by_source_result_id,
    get_diagnostic_result,
    get_diagnostic_session,
    list_check_outcomes,
    list_confirmed_cases,
    list_diagnostic_sessions,
    update_check_outcome,
    update_hypothesis_outcome,
)
from app.db.database import get_db
from app.schemas import (
    ConfirmedDiagnosticCaseConfirmRequest,
    ConfirmedDiagnosticCaseCreate,
    ConfirmedDiagnosticCaseRead,
    DiagnosticAnalyzeRequest,
    DiagnosticAnalyzeResponse,
    DiagnosticCheckOutcomeCreate,
    DiagnosticCheckOutcomeRead,
    DiagnosticCheckOutcomeUpdate,
    DiagnosticResultCreate,
    DiagnosticResultRead,
    DiagnosticSessionCreate,
    DiagnosticSessionRead,
    HypothesisOutcomeUpdate,
)
from app.services.diagnostic import DiagnosticService, DiagnosticServiceError, get_diagnostic_service
from app.services.diagnostic_analytics import get_diagnostic_analytics_service
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
    if request.session_id is not None:
        raise HTTPException(
            status_code=422,
            detail="session_id is not allowed on /analyze. Use /sessions/{session_id}/analyze for follow-up analysis.",
        )
    diagnostic_service = get_diagnostic_service(embedding_service, llm_service)
    try:
        return diagnostic_service.analyze(db, request)
    except DiagnosticServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/sessions/{session_id}/analyze", response_model=DiagnosticAnalyzeResponse, status_code=201)
def analyze_in_session(
    session_id: uuid.UUID,
    request: DiagnosticAnalyzeRequest,
    db: Session = Depends(get_db),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    llm_service: LLMService = Depends(get_llm_service),
) -> DiagnosticAnalyzeResponse:
    if request.session_id is not None and request.session_id != session_id:
        raise HTTPException(
            status_code=422,
            detail="request.session_id must match the URL session_id.",
        )
    session = get_diagnostic_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Diagnostic session not found")
    diagnostic_service = get_diagnostic_service(embedding_service, llm_service)
    try:
        return diagnostic_service.analyze(db, request, session=session)
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


@router.patch("/results/{result_id}/outcome", response_model=DiagnosticResultRead)
def update_result_outcome(
    result_id: uuid.UUID,
    outcome_in: HypothesisOutcomeUpdate,
    db: Session = Depends(get_db),
) -> DiagnosticResultRead:
    result = update_hypothesis_outcome(db, result_id, outcome_in)
    if result is None:
        raise HTTPException(status_code=404, detail="Diagnostic result not found")
    return result


@router.post("/results/{result_id}/checks", response_model=DiagnosticCheckOutcomeRead, status_code=201)
def create_result_check_outcome(
    result_id: uuid.UUID,
    check_in: DiagnosticCheckOutcomeCreate,
    db: Session = Depends(get_db),
) -> DiagnosticCheckOutcomeRead:
    result = get_diagnostic_result(db, result_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Diagnostic result not found")
    return create_check_outcome(db, result_id, check_in)


@router.patch("/checks/{outcome_id}", response_model=DiagnosticCheckOutcomeRead)
def update_check_outcome_endpoint(
    outcome_id: uuid.UUID,
    check_update: DiagnosticCheckOutcomeUpdate,
    db: Session = Depends(get_db),
) -> DiagnosticCheckOutcomeRead:
    outcome = update_check_outcome(db, outcome_id, check_update)
    if outcome is None:
        raise HTTPException(status_code=404, detail="Diagnostic check outcome not found")
    return outcome


@router.get("/results/{result_id}/checks", response_model=list[DiagnosticCheckOutcomeRead])
def list_result_checks(
    result_id: uuid.UUID, db: Session = Depends(get_db)
) -> list[DiagnosticCheckOutcomeRead]:
    result = get_diagnostic_result(db, result_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Diagnostic result not found")
    return list_check_outcomes(db, result_id)


@router.get("/analytics/outcomes")
def get_outcome_analytics(db: Session = Depends(get_db)) -> dict:
    service = get_diagnostic_analytics_service(db)
    return service.get_outcome_analytics().model_dump()


@router.post("/results/{result_id}/confirmed-case", response_model=ConfirmedDiagnosticCaseRead)
def create_confirmed_case_from_result(
    result_id: uuid.UUID,
    case_in: ConfirmedDiagnosticCaseConfirmRequest,
    db: Session = Depends(get_db),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
) -> ConfirmedDiagnosticCaseRead:
    result = get_diagnostic_result(db, result_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Diagnostic result not found")
    existing = get_confirmed_case_by_source_result_id(db, result_id)
    if existing is not None:
        return JSONResponse(content=ConfirmedDiagnosticCaseRead.model_validate(existing).model_dump(mode="json"), status_code=200)
    session = get_diagnostic_session(db, result.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Diagnostic session not found")
    diagnostic_service = get_diagnostic_service(embedding_service, get_llm_service())
    try:
        confirmed_case = diagnostic_service.create_confirmed_case_from_result(
            db, session, result,
            confirmed_fault=case_in.confirmed_fault,
            confirmed_fault_description=case_in.confirmed_fault_description,
            repair_suggestion=case_in.repair_suggestion,
            severity=case_in.severity,
        )
    except Exception:
        db.rollback()
        existing = get_confirmed_case_by_source_result_id(db, result_id)
        if existing is not None:
            return JSONResponse(content=ConfirmedDiagnosticCaseRead.model_validate(existing).model_dump(mode="json"), status_code=200)
        raise
    return JSONResponse(content=ConfirmedDiagnosticCaseRead.model_validate(confirmed_case).model_dump(mode="json"), status_code=201)


@router.get("/confirmed-cases", response_model=list[ConfirmedDiagnosticCaseRead])
def read_confirmed_cases(
    make: str | None = None,
    model: str | None = None,
    year: int | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> list[ConfirmedDiagnosticCaseRead]:
    return list_confirmed_cases(db, skip=skip, limit=limit, make=make, model=model, year=year)
