import re
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import models
from app.schemas import (
    DiagnosticCheckOutcomeCreate,
    DiagnosticCheckOutcomeUpdate,
    DiagnosticConversationMessageCreate,
    DiagnosticResultCreate,
    DiagnosticSessionCreate,
    HypothesisOutcomeUpdate,
    KnowledgeEntryCreate,
)

_DTC_PATTERN = re.compile(r"\b[PCBU][0-9]{4}\b", re.IGNORECASE)


def _extract_dtc_codes(text: str) -> set[str]:
    return {match.upper() for match in _DTC_PATTERN.findall(text)}


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


def get_existing_entry_keys(db: Session) -> set[tuple[str, str | None]]:
    rows = db.execute(
        select(models.KnowledgeEntry.category, models.KnowledgeEntry.entry_key)
    ).all()
    return {(row.category, row.entry_key) for row in rows}


def bulk_create_knowledge_entries(
    db: Session, entries: list[KnowledgeEntryCreate], skip_existing: bool = True
) -> tuple[int, int, list[str]]:
    created = 0
    skipped = 0
    errors: list[str] = []

    existing_keys = get_existing_entry_keys(db) if skip_existing else set()

    for idx, entry_in in enumerate(entries):
        key = (entry_in.category, entry_in.entry_key)
        if skip_existing and key in existing_keys:
            skipped += 1
            continue
        try:
            entry = models.KnowledgeEntry(**entry_in.model_dump())
            db.add(entry)
            existing_keys.add(key)
            created += 1
        except Exception as exc:
            errors.append(f"Entry {idx}: {exc}")

    if created:
        db.commit()
    return created, skipped, errors


def get_knowledge_entry(db: Session, entry_id: uuid.UUID) -> models.KnowledgeEntry | None:
    return db.get(models.KnowledgeEntry, entry_id)


def list_knowledge_entries(
    db: Session, skip: int = 0, limit: int = 100, category: str | None = None
) -> list[models.KnowledgeEntry]:
    query = db.query(models.KnowledgeEntry)
    if category:
        query = query.filter(models.KnowledgeEntry.category == category)
    return query.offset(skip).limit(limit).all()


def search_knowledge_entries(
    db: Session,
    query_embedding: list[float],
    category: str | None = None,
    top_k: int = 5,
) -> list[models.KnowledgeEntry]:
    distance = models.KnowledgeEntry.embedding.cosine_distance(query_embedding)
    stmt = select(models.KnowledgeEntry, distance.label("distance")).where(
        models.KnowledgeEntry.embedding.is_not(None)
    )
    if category:
        stmt = stmt.where(models.KnowledgeEntry.category == category)
    stmt = stmt.order_by(distance).limit(top_k)
    return db.execute(stmt).all()


def update_knowledge_entry_embedding(
    db: Session, entry_id: uuid.UUID, embedding: list[float]
) -> models.KnowledgeEntry | None:
    entry = get_knowledge_entry(db, entry_id)
    if entry is None:
        return None
    entry.embedding = embedding
    db.commit()
    db.refresh(entry)
    return entry


def hybrid_search_knowledge_entries(
    db: Session,
    query_embedding: list[float] | None,
    query_text: str,
    category: str | None = None,
    top_k: int = 5,
    request_components: list[str] | None = None,
) -> list[tuple[models.KnowledgeEntry, float]]:
    dtc_codes = _extract_dtc_codes(query_text)

    semantic_rows = []
    if query_embedding is not None:
        semantic_top_k = max(top_k * 3, 20)
        semantic_rows = search_knowledge_entries(db, query_embedding, category, semantic_top_k)

    tsquery = func.plainto_tsquery("english", query_text)
    keyword_stmt = (
        select(models.KnowledgeEntry, func.ts_rank(models.KnowledgeEntry.search_vector, tsquery).label("keyword_rank"))
        .where(models.KnowledgeEntry.search_vector.op("@@")(tsquery))
    )
    if category:
        keyword_stmt = keyword_stmt.where(models.KnowledgeEntry.category == category)
    keyword_stmt = keyword_stmt.order_by(func.ts_rank(models.KnowledgeEntry.search_vector, tsquery).desc()).limit(max(top_k * 3, 20))
    keyword_rows = db.execute(keyword_stmt).all()

    entry_scores: dict[uuid.UUID, tuple[models.KnowledgeEntry, float, float]] = {}

    for entry, distance in semantic_rows:
        semantic_score = 1.0 - float(distance)
        keyword_score = 0.0
        if entry.entry_key and entry.entry_key.upper() in dtc_codes:
            keyword_score = max(keyword_score, 1.0)
        entry_scores[entry.id] = (entry, semantic_score, keyword_score)

    for entry, keyword_rank in keyword_rows:
        keyword_score = min(float(keyword_rank), 1.0)
        if entry.entry_key and entry.entry_key.upper() in dtc_codes:
            keyword_score = max(keyword_score, 1.0)
        if entry.id in entry_scores:
            existing_entry, semantic_score, existing_keyword_score = entry_scores[entry.id]
            entry_scores[entry.id] = (existing_entry, semantic_score, max(existing_keyword_score, keyword_score))
        else:
            entry_scores[entry.id] = (entry, 0.0, keyword_score)

    # Compute component match bonus for each entry
    component_match_bonus: dict[uuid.UUID, float] = {}
    if request_components:
        from app.services.component_taxonomy import map_knowledge_entry
        for entry_id, (entry, _, _) in entry_scores.items():
            component = map_knowledge_entry(entry.entry_key or "", entry.category)
            if component and component.component_id in request_components:
                component_match_bonus[entry_id] = 0.3

    scored: list[tuple[models.KnowledgeEntry, float]] = []
    for entry_id, (entry, semantic_score, keyword_score) in entry_scores.items():
        dtc_bonus = 0.0
        if entry.entry_key and entry.entry_key.upper() in dtc_codes:
            dtc_bonus = 0.5
        comp_bonus = component_match_bonus.get(entry_id, 0.0)
        combined_score = semantic_score + keyword_score * 0.3 + dtc_bonus + comp_bonus
        scored.append((entry, combined_score))

    # Deterministic sort: score desc, then entry_key asc for stable ordering
    scored.sort(key=lambda x: (-x[1], x[0].entry_key or ""))

    # Content-based deduplication: remove entries with very similar content
    # Keep the highest-scored entry for each content cluster
    if len(scored) > 1:
        deduped: list[tuple[models.KnowledgeEntry, float]] = []
        for entry, score in scored:
            # Check if this content is too similar to already selected entries
            is_duplicate = False
            for existing_entry, _ in deduped:
                if entry.content == existing_entry.content:
                    is_duplicate = True
                    break
            if not is_duplicate:
                deduped.append((entry, score))
        scored = deduped

    return scored[:top_k]


def get_diagnostic_result(db: Session, result_id: uuid.UUID) -> models.DiagnosticResult | None:
    return db.get(models.DiagnosticResult, result_id)


def update_hypothesis_outcome(
    db: Session, result_id: uuid.UUID, outcome_in: HypothesisOutcomeUpdate
) -> models.DiagnosticResult | None:
    result = get_diagnostic_result(db, result_id)
    if result is None:
        return None
    result.hypothesis_status = outcome_in.hypothesis_status
    result.observed_result = outcome_in.observed_result
    db.commit()
    db.refresh(result)
    return result


def create_check_outcome(
    db: Session, result_id: uuid.UUID, check_in: DiagnosticCheckOutcomeCreate
) -> models.DiagnosticCheckOutcome:
    outcome = models.DiagnosticCheckOutcome(result_id=result_id, **check_in.model_dump())
    db.add(outcome)
    db.commit()
    db.refresh(outcome)
    return outcome


def get_check_outcome(db: Session, outcome_id: uuid.UUID) -> models.DiagnosticCheckOutcome | None:
    return db.get(models.DiagnosticCheckOutcome, outcome_id)


def update_check_outcome(
    db: Session, outcome_id: uuid.UUID, check_update: DiagnosticCheckOutcomeUpdate
) -> models.DiagnosticCheckOutcome | None:
    outcome = get_check_outcome(db, outcome_id)
    if outcome is None:
        return None
    if check_update.status is not None:
        outcome.status = check_update.status
    if check_update.observed_result is not None:
        outcome.observed_result = check_update.observed_result
    if check_update.technician_note is not None:
        outcome.technician_note = check_update.technician_note
    db.commit()
    db.refresh(outcome)
    return outcome


def list_check_outcomes(db: Session, result_id: uuid.UUID) -> list[models.DiagnosticCheckOutcome]:
    return db.query(models.DiagnosticCheckOutcome).filter(models.DiagnosticCheckOutcome.result_id == result_id).all()


def create_conversation_message(
    db: Session, session_id: uuid.UUID, message_in: DiagnosticConversationMessageCreate
) -> models.DiagnosticConversationMessage:
    message = models.DiagnosticConversationMessage(session_id=session_id, **message_in.model_dump())
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def get_conversation_messages(db: Session, session_id: uuid.UUID) -> list[models.DiagnosticConversationMessage]:
    return (
        db.query(models.DiagnosticConversationMessage)
        .filter(models.DiagnosticConversationMessage.session_id == session_id)
        .order_by(models.DiagnosticConversationMessage.turn_index)
        .all()
    )
