import json
import uuid
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.config import Settings, settings
from app.crud import (
    create_conversation_message,
    create_diagnostic_result,
    create_diagnostic_session,
    create_confirmed_case,
    get_conversation_messages,
    hybrid_search_knowledge_entries,
    search_confirmed_cases,
)
from app.db import models
from app.db.database import engine
from app.schemas import (
    DiagnosticAnalyzeRequest,
    DiagnosticAnalyzeResponse,
    DiagnosticConversationMessageCreate,
    DiagnosticHypothesis,
    DiagnosticResultCreate,
    DiagnosticSessionCreate,
    EvidenceReference,
    KnowledgeSearchResult,
)
from app.services.component_taxonomy import (
    map_evidence_to_component,
    map_fault_description,
    map_knowledge_entry,
)
from app.services.embeddings import EmbeddingService
from app.services.llm import LLMProviderError, LLMService
from app.services.repair_safety import RepairSafetyTier, determine_repair_safety_tier, SafetyTierDecision


class DiagnosticServiceError(Exception):
    pass


@dataclass
class ConfidenceFactors:
    """Factors used for deterministic confidence calibration."""
    evidence_count: int
    avg_similarity: float
    has_dtc_match: bool
    component_mapped: bool
    symptom_match: bool
    conflicting_evidence: int = 0


class DiagnosticService:
    def __init__(
        self,
        app_settings: Settings,
        embedding_service: EmbeddingService,
        llm_service: LLMService,
    ) -> None:
        self._settings = app_settings
        self._embedding_service = embedding_service
        self._llm_service = llm_service

    def _build_search_query(self, request: DiagnosticAnalyzeRequest) -> str:
        parts: list[str] = []

        if request.dtc_codes:
            parts.append("DTCs:\n" + "\n".join(request.dtc_codes))

        parts.append("Symptoms:\n" + request.symptom_text)

        if request.make or request.model or request.year:
            vehicle_parts = [
                p for p in [request.make, request.model, str(request.year) if request.year else None] if p
            ]
            if vehicle_parts:
                parts.append("Vehicle:\n" + " ".join(vehicle_parts))

        return "\n\n".join(parts)

    _MAX_HISTORY_TURNS = 3
    _MAX_HISTORY_FAULT_DESC_LEN = 200
    _MAX_HISTORY_SYMPTOM_LEN = 100

    def _build_session_context(
        self, session: models.DiagnosticSession, follow_up_answer: str | None = None
    ) -> str:
        results = session.results
        if not results:
            return ""

        recent = results[-self._MAX_HISTORY_TURNS:]
        lines: list[str] = ["Previous diagnostic turns (most recent last):"]

        confirmed: list[str] = []
        rejected: list[str] = []
        unconfirmed: list[str] = []

        for result in recent:
            dtcs = session.dtc_codes or "None"
            symptom = session.symptom_text[: self._MAX_HISTORY_SYMPTOM_LEN]
            fault = result.fault_description[: self._MAX_HISTORY_FAULT_DESC_LEN]
            status = result.hypothesis_status or "proposed"
            checks = ", ".join(result.recommended_checks or [])[:200]
            observed = result.observed_result or ""
            check_outcomes = result.check_outcomes or []

            turn_lines = [
                f"- DTCs: {dtcs}",
                f"  Symptoms: {symptom}",
                f"  Hypothesis: {fault} (confidence: {result.confidence_score}, severity: {result.severity}, status: {status})",
            ]
            if checks:
                turn_lines.append(f"  Recommended checks: {checks}")
            if observed:
                turn_lines.append(f"  Observed result: {observed}")
            if check_outcomes:
                for co in check_outcomes:
                    turn_lines.append(f"  Check [{co.status}]: {co.check_description}")
                    if co.observed_result:
                        turn_lines.append(f"    Observed: {co.observed_result}")

            turn_text = "\n".join(turn_lines)
            if status == "confirmed":
                confirmed.append(turn_text)
            elif status == "rejected":
                rejected.append(turn_text)
            else:
                unconfirmed.append(turn_text)

        if confirmed:
            lines.append("\nCONFIRMED HYPOTHESES:")
            lines.extend(confirmed)
        if rejected:
            lines.append("\nREJECTED HYPOTHESES (do not treat as active causes):")
            lines.extend(rejected)
        if unconfirmed:
            lines.append("\nUNCONFIRMED HYPOTHESES:")
            lines.extend(unconfirmed)

        if follow_up_answer:
            lines.append(f"\nUSER FOLLOW-UP ANSWER: {follow_up_answer}")

        return "\n".join(lines)

    def _build_conversation_context(
        self, session: models.DiagnosticSession
    ) -> str:
        """Build conversation context from persisted messages."""
        messages = get_conversation_messages(self._session_db, session.id) if hasattr(self, '_session_db') else []
        # Fallback to session relationship if available
        if not messages and session.conversation_messages:
            messages = session.conversation_messages

        if not messages:
            return ""

        # Apply context limit from settings
        max_messages = self._settings.diagnostic_max_conversation_messages
        recent_messages = messages[-max_messages:] if len(messages) > max_messages else messages

        lines: list[str] = ["Previous conversation (most recent last):"]
        for msg in recent_messages:
            role_label = "User" if msg.role == "user" else "Assistant"
            lines.append(f"{role_label}: {msg.content}")

        return "\n".join(lines)

    def _count_follow_up_turns(self, session: models.DiagnosticSession) -> int:
        """Count the number of follow-up turns (assistant questions) in the conversation."""
        messages = get_conversation_messages(self._session_db, session.id) if hasattr(self, '_session_db') else []
        if not messages and session.conversation_messages:
            messages = session.conversation_messages

        # Count assistant messages that are follow-up questions
        # A follow-up turn is when assistant asks a question (needs_more_information)
        follow_up_count = 0
        for msg in messages:
            if msg.role == "assistant":
                follow_up_count += 1
        return follow_up_count

    def _persist_user_message(self, db: Session, session_id: uuid.UUID, content: str, turn_index: int) -> None:
        """Persist a user message to the conversation."""
        message_in = DiagnosticConversationMessageCreate(
            role="user",
            content=content,
            turn_index=turn_index,
        )
        create_conversation_message(db, session_id, message_in)

    def _persist_assistant_message(self, db: Session, session_id: uuid.UUID, content: str, turn_index: int) -> None:
        """Persist an assistant message to the conversation."""
        message_in = DiagnosticConversationMessageCreate(
            role="assistant",
            content=content,
            turn_index=turn_index,
        )
        create_conversation_message(db, session_id, message_in)

    def _get_next_turn_index(self, session: models.DiagnosticSession) -> int:
        """Get the next turn index for the conversation."""
        messages = get_conversation_messages(self._session_db, session.id) if hasattr(self, '_session_db') else []
        if not messages and session.conversation_messages:
            messages = session.conversation_messages

        if not messages:
            return 0
        return max(msg.turn_index for msg in messages) + 1

    def _format_evidence(self, evidence: list[KnowledgeSearchResult]) -> str:
        lines: list[str] = []
        for idx, item in enumerate(evidence, start=1):
            lines.append(
                f"{idx}. [{item.category}] {item.entry_key or 'n/a'} "
                f"(similarity {item.similarity_score}): {item.content}"
            )
        return "\n".join(lines) if lines else "No relevant knowledge entries were retrieved."

    def _build_evidence_catalog(self, evidence: list[KnowledgeSearchResult]) -> str:
        """Build a structured catalog of evidence for the LLM to reference by ID."""
        if not evidence:
            return "No evidence available."
        
        lines: list[str] = ["EVIDENCE CATALOG (reference these by evidence_id in your response):"]
        for item in evidence:
            lines.append(
                f"  evidence_id: {item.id} | "
                f"category: {item.category} | "
                f"entry_key: {item.entry_key or 'n/a'} | "
                f"similarity: {item.similarity_score:.3f} | "
                f"content: {item.content}"
            )
        return "\n".join(lines)

    def _build_prompt(
        self,
        request: DiagnosticAnalyzeRequest,
        evidence: list[KnowledgeSearchResult],
        historical_cases: list[tuple[models.ConfirmedDiagnosticCase, float]] | None = None,
        session_context: str = "",
        conversation_context: str = "",
    ) -> str:
        query = self._build_search_query(request)
        vehicle = " ".join(
            p for p in [request.make, request.model, str(request.year) if request.year else None] if p
        ) or "Unknown vehicle"
        dtcs = ", ".join(request.dtc_codes) if request.dtc_codes else "None provided"

        context_section = ""
        if session_context or conversation_context:
            context_parts = []
            if session_context:
                context_parts.append(f"PREVIOUS SESSION CONTEXT\n{session_context}")
            if conversation_context:
                context_parts.append(f"CONVERSATION HISTORY\n{conversation_context}")
            context_section = "\n\n".join(context_parts) + """

Notes:
- The hypotheses above are prior possibilities, not confirmed facts.
- Focus on the current symptoms and evidence. Do not assume prior hypotheses are correct.
- If the current symptoms suggest a different cause than previously hypothesized, say so.
- The conversation history shows the actual dialogue between the user and assistant.

"""

        evidence_catalog = self._build_evidence_catalog(evidence)

        historical_section = ""
        if historical_cases:
            lines = ["HISTORICAL CONFIRMED CASES (similar past diagnoses):"]
            for idx, (case, score) in enumerate(historical_cases, start=1):
                lines.append(f"{idx}. Vehicle: {case.make or 'Unknown'} {case.model or ''} {case.year or ''}")
                if case.dtc_codes:
                    lines.append(f"   DTCs: {case.dtc_codes}")
                lines.append(f"   Symptoms: {case.symptom_text}")
                lines.append(f"   Confirmed fault: {case.confirmed_fault}")
                if case.repair_suggestion:
                    lines.append(f"   Repair: {case.repair_suggestion}")
                lines.append(f"   Similarity: {score:.2f}")
            historical_section = "\n".join(lines) + "\n\n"

        return f"""You are an expert automotive diagnostic assistant.

Analyze the following case and produce structured diagnostic reasoning.

Vehicle: {vehicle}
DTC codes: {dtcs}
Symptoms: {request.symptom_text}
{context_section}{historical_section}{evidence_catalog}

Instructions:
- Use ONLY the retrieved evidence above as supporting facts. Do not invent automotive knowledge.
- Historical confirmed cases are provided for reference only; they are not guaranteed to apply to this vehicle.
- If evidence is insufficient, clearly state uncertainty and recommend checks before repair.
- Each hypothesis must include a confidence score between 0 and 1 that reflects the available evidence.
- Severity must be one of: low, medium, high, critical.
- Provide concrete recommended checks a technician should perform.
- Provide a repair suggestion only when the evidence reasonably supports it.
- If more information is needed from the user to narrow down the diagnosis, set "needs_more_information" to true and provide a specific follow-up question with reasoning.
- The follow-up question should be specific and actionable for a vehicle owner.
- For each hypothesis, reference supporting evidence by evidence_id from the catalog above.
- If multiple plausible causes exist, return them as a differential diagnosis ranked by likelihood.
- If evidence conflicts between hypotheses, note this and prefer asking a follow-up question.

Return a single JSON object with this schema:
{{
  "status": "complete" | "needs_more_information",
  "follow_up_question": "string or null",
  "follow_up_reason": "string or null",
  "hypotheses": [
    {{
      "fault_description": "string",
      "confidence_score": 0.0,
      "severity": "low|medium|high|critical",
      "supporting_evidence": ["string"],
      "recommended_checks": ["string"],
      "repair_suggestion": "string or null",
      "evidence_references": [
        {{
          "evidence_id": "uuid",
          "category": "string",
          "entry_key": "string or null",
          "excerpt": "string",
          "similarity_score": 0.0,
          "relevance": "supporting|conflicting|contextual"
        }}
      ],
      "differential_rank": 1
    }}
  ]
}}
"""

    @staticmethod
    def _coerce_string_list(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        coerced: list[str] = []
        for item in value:
            if isinstance(item, str):
                stripped = item.strip()
                if stripped:
                    coerced.append(stripped)
        return coerced

    def _validate_evidence(
        self,
        hypothesis: DiagnosticHypothesis,
        evidence: list[KnowledgeSearchResult],
    ) -> tuple[list[str], list[uuid.UUID]]:
        """Filter LLM supporting evidence against retrieved knowledge entries.

        Returns validated evidence strings and the IDs of the knowledge entries
        they reference. Unmatched references are dropped as hallucinations.
        """
        if not evidence:
            return [], []

        # Build multiple matchable descriptors for each retrieved entry.
        entry_by_descriptor: dict[str, uuid.UUID] = {}
        for item in evidence:
            if item.entry_key:
                entry_by_descriptor[item.entry_key.lower()] = item.id
            entry_by_descriptor[f"[{item.category}] {item.entry_key or 'n/a'}".lower()] = item.id

        validated_strings: list[str] = []
        validated_ids: list[uuid.UUID] = []
        seen_ids: set[uuid.UUID] = set()

        for reference in hypothesis.supporting_evidence:
            if not isinstance(reference, str):
                continue

            ref_lower = reference.lower().strip()
            if not ref_lower:
                continue

            matched_id: uuid.UUID | None = None

            # Exact descriptor match.
            if ref_lower in entry_by_descriptor:
                matched_id = entry_by_descriptor[ref_lower]
            else:
                # Fuzzy match against entry keys and content.
                for item in evidence:
                    if item.entry_key and item.entry_key.lower() in ref_lower:
                        matched_id = item.id
                        break
                    item_text = f"{item.category} {item.entry_key or ''} {item.content}".lower()
                    if ref_lower in item_text or item.content.lower() in ref_lower:
                        matched_id = item.id
                        break

            if matched_id is not None:
                validated_strings.append(reference)
                if matched_id not in seen_ids:
                    validated_ids.append(matched_id)
                    seen_ids.add(matched_id)

        return validated_strings, validated_ids

    def _validate_evidence_references(
        self,
        evidence_references: list[EvidenceReference],
        evidence: list[KnowledgeSearchResult],
    ) -> list[EvidenceReference]:
        """Validate structured evidence references against retrieved knowledge.

        Returns only those references that match retrieved evidence.
        Invalid or hallucinated references are dropped.
        """
        if not evidence or not evidence_references:
            return []

        # Build lookup by evidence_id
        evidence_by_id: dict[uuid.UUID, KnowledgeSearchResult] = {item.id: item for item in evidence}

        validated: list[EvidenceReference] = []
        seen_ids: set[uuid.UUID] = set()

        for ref in evidence_references:
            # Validate evidence_id exists in retrieved evidence
            if ref.evidence_id not in evidence_by_id:
                continue

            matched_evidence = evidence_by_id[ref.evidence_id]

            # Validate category matches
            if ref.category != matched_evidence.category:
                continue

            # Validate entry_key matches (if provided)
            if ref.entry_key is not None and matched_evidence.entry_key != ref.entry_key:
                continue

            # Validate similarity_score is reasonable (within 0.1 of actual)
            if abs(ref.similarity_score - matched_evidence.similarity_score) > 0.1:
                continue

            # Check for duplicates
            if ref.evidence_id in seen_ids:
                continue

            # Create validated reference with correct data from retrieved evidence
            validated_ref = EvidenceReference(
                evidence_id=matched_evidence.id,
                category=matched_evidence.category,
                entry_key=matched_evidence.entry_key,
                excerpt=matched_evidence.content[:200],  # Use actual content as excerpt
                similarity_score=matched_evidence.similarity_score,
                relevance=ref.relevance,
            )
            validated.append(validated_ref)
            seen_ids.add(ref.evidence_id)

        return validated

    def _build_evidence_references(
        self,
        validated_ids: list[uuid.UUID],
        evidence: list[KnowledgeSearchResult],
    ) -> list[EvidenceReference]:
        """Build structured EvidenceReference objects from validated evidence IDs."""
        evidence_by_id: dict[uuid.UUID, KnowledgeSearchResult] = {item.id: item for item in evidence}
        references: list[EvidenceReference] = []

        for ev_id in validated_ids:
            if ev_id in evidence_by_id:
                item = evidence_by_id[ev_id]
                references.append(EvidenceReference(
                    evidence_id=item.id,
                    category=item.category,
                    entry_key=item.entry_key,
                    excerpt=item.content[:200],
                    similarity_score=item.similarity_score,
                    relevance="supporting",
                ))
        return references

    def _detect_conflicting_evidence(
        self,
        hypotheses: list[DiagnosticHypothesis],
        evidence: list[KnowledgeSearchResult],
    ) -> dict[uuid.UUID, list[uuid.UUID]]:
        """Detect evidence that supports multiple competing hypotheses.

        Returns a mapping of evidence_id -> list of hypothesis indices that reference it.
        """
        evidence_usage: dict[uuid.UUID, list[int]] = {}

        for idx, hypothesis in enumerate(hypotheses):
            for ref in hypothesis.evidence_references:
                if ref.evidence_id not in evidence_usage:
                    evidence_usage[ref.evidence_id] = []
                evidence_usage[ref.evidence_id].append(idx)

        # Filter to only evidence used by multiple hypotheses
        conflicting = {eid: indices for eid, indices in evidence_usage.items() if len(indices) > 1}
        return conflicting

    def _assess_evidence_quality(self, hypothesis: DiagnosticHypothesis, evidence: list[KnowledgeSearchResult]) -> str:
        """Assess the quality of evidence supporting a hypothesis."""
        if not hypothesis.evidence_references:
            return "insufficient"

        evidence_by_id: dict[uuid.UUID, KnowledgeSearchResult] = {item.id: item for item in evidence}

        supporting_count = 0
        total_similarity = 0.0
        has_dtc_match = False

        for ref in hypothesis.evidence_references:
            if ref.relevance != "supporting":
                continue
            if ref.evidence_id in evidence_by_id:
                item = evidence_by_id[ref.evidence_id]
                supporting_count += 1
                total_similarity += item.similarity_score
                if item.category == "dtc" or (item.entry_key and item.entry_key.upper().startswith("P")):
                    has_dtc_match = True

        if supporting_count == 0:
            return "insufficient"

        avg_similarity = total_similarity / supporting_count

        # Strong: multiple high-similarity evidence items or DTC match with good similarity
        if supporting_count >= 3 and avg_similarity >= 0.7:
            return "strong"
        if supporting_count >= 2 and avg_similarity >= 0.75:
            return "strong"
        if has_dtc_match and avg_similarity >= 0.6:
            return "strong"

        # Moderate: some evidence with decent similarity
        if supporting_count >= 2 and avg_similarity >= 0.5:
            return "moderate"
        if supporting_count >= 1 and avg_similarity >= 0.7:
            return "moderate"

        # Weak: limited or low-similarity evidence
        if supporting_count >= 1:
            return "weak"

        return "insufficient"

    def _calibrate_confidence(
        self,
        llm_confidence: float,
        hypothesis: DiagnosticHypothesis,
        evidence: list[KnowledgeSearchResult],
        request: DiagnosticAnalyzeRequest,
    ) -> float:
        """Apply deterministic confidence calibration based on evidence factors.

        Only adjusts confidence when there is validated evidence to base the
        calibration on. If no evidence was validated, returns the original
        LLM confidence to preserve backward compatibility.
        """
        # Check if we have any validated evidence (structured or string-based)
        has_validated_evidence = (
            (hypothesis.evidence_references and any(r.relevance == "supporting" for r in hypothesis.evidence_references))
            or hypothesis.supporting_evidence
        )

        # If no validated evidence, don't penalize - return original confidence
        # This preserves backward compatibility with tests and cases where
        # the knowledge base has no relevant entries
        if not has_validated_evidence:
            return llm_confidence

        evidence_by_id: dict[uuid.UUID, KnowledgeSearchResult] = {item.id: item for item in evidence}

        factors = ConfidenceFactors(
            evidence_count=len([r for r in hypothesis.evidence_references if r.relevance == "supporting"]) if hypothesis.evidence_references else len(hypothesis.supporting_evidence),
            avg_similarity=0.0,
            has_dtc_match=False,
            component_mapped=hypothesis.component_id is not None,
            symptom_match=False,
        )

        supporting_refs = [r for r in hypothesis.evidence_references if r.relevance == "supporting"] if hypothesis.evidence_references else []
        if supporting_refs:
            similarities = []
            for ref in supporting_refs:
                if ref.evidence_id in evidence_by_id:
                    item = evidence_by_id[ref.evidence_id]
                    similarities.append(item.similarity_score)
                    if item.category == "dtc" or (item.entry_key and item.entry_key.upper().startswith("P")):
                        factors.has_dtc_match = True
            factors.avg_similarity = sum(similarities) / len(similarities) if similarities else 0.0

        # Check symptom match - simple keyword overlap
        symptom_lower = request.symptom_text.lower()
        for ref in supporting_refs:
            if ref.evidence_id in evidence_by_id:
                item = evidence_by_id[ref.evidence_id]
                item_text = f"{item.category} {item.entry_key or ''} {item.content}".lower()
                # Check for significant keyword overlap
                symptom_words = set(symptom_lower.split())
                evidence_words = set(item_text.split())
                overlap = symptom_words & evidence_words
                if len(overlap) >= 2:
                    factors.symptom_match = True
                    break

        # Base calibration - start with LLM confidence
        calibrated = llm_confidence

        # Evidence count factor - modest adjustments
        if factors.evidence_count >= 3:
            calibrated = min(calibrated * 1.03, 1.0)
        elif factors.evidence_count == 2:
            calibrated = calibrated * 1.0
        elif factors.evidence_count == 1:
            calibrated = calibrated * 0.98
        else:
            calibrated = calibrated * 0.95  # Mild penalty

        # Similarity factor
        if factors.avg_similarity >= 0.8:
            calibrated = min(calibrated * 1.03, 1.0)
        elif factors.avg_similarity >= 0.6:
            calibrated = calibrated * 1.0
        elif factors.avg_similarity >= 0.4:
            calibrated = calibrated * 0.99
        else:
            calibrated = calibrated * 0.97

        # DTC match bonus
        if factors.has_dtc_match:
            calibrated = min(calibrated * 1.03, 1.0)

        # Component mapping bonus
        if factors.component_mapped:
            calibrated = min(calibrated * 1.03, 1.0)

        # Symptom match bonus
        if factors.symptom_match:
            calibrated = min(calibrated * 1.03, 1.0)

        # Conflicting evidence penalty - mild
        if hasattr(hypothesis, '_conflicting_count') and hypothesis._conflicting_count > 0:
            calibrated = calibrated * max(0.9, 1.0 - 0.03 * hypothesis._conflicting_count)

        # Clamp to valid range
        return max(0.0, min(1.0, round(calibrated, 2)))

    def _rank_differential(
        self,
        hypotheses: list[DiagnosticHypothesis],
        evidence: list[KnowledgeSearchResult],
    ) -> list[DiagnosticHypothesis]:
        """Rank hypotheses for differential diagnosis and assign ranks."""
        if not hypotheses:
            return hypotheses

        # Sort by calibrated confidence (descending)
        ranked = sorted(hypotheses, key=lambda h: h.confidence_score, reverse=True)

        # Assign differential ranks
        for rank, hypothesis in enumerate(ranked, start=1):
            hypothesis.differential_rank = rank

        return ranked

    def _should_request_follow_up(
        self,
        hypotheses: list[DiagnosticHypothesis],
        evidence: list[KnowledgeSearchResult],
        request: DiagnosticAnalyzeRequest,
    ) -> tuple[bool, str | None, str | None]:
        """Determine if a follow-up question is needed and what it should be."""
        if not hypotheses:
            return True, "Could you describe the symptoms in more detail?", "No hypotheses generated"

        # Check if top hypothesis has insufficient evidence
        top_hypothesis = hypotheses[0]
        if top_hypothesis.evidence_quality in ("weak", "insufficient"):
            return True, (
                "Could you provide more details about when the symptom occurs "
                "(e.g., only during acceleration, at idle, when cold)?"
            ), "Top hypothesis has weak or insufficient evidence"

        # Check for conflicting evidence between top hypotheses
        if len(hypotheses) >= 2:
            conflicting = self._detect_conflicting_evidence(hypotheses, evidence)
            if conflicting:
                # There's evidence supporting multiple hypotheses - ask for clarification
                return True, (
                    "Does the symptom change under specific conditions "
                    "(e.g., load, temperature, RPM range)?"
                ), "Conflicting evidence between competing hypotheses"

        # Check if we have DTC codes but no DTC-matched evidence
        if request.dtc_codes:
            has_dtc_evidence = any(
                item.category == "dtc" or (item.entry_key and item.entry_key.upper().startswith("P"))
                for item in evidence
            )
            if not has_dtc_evidence:
                return True, (
                    f"The DTC code(s) {', '.join(request.dtc_codes)} were not found in the knowledge base. "
                    "Can you confirm the exact code or describe any other symptoms?"
                ), "DTC codes not matched in knowledge base"

        return False, None, None

    def _parse_hypotheses(self, raw: str) -> list[DiagnosticHypothesis]:
        """Backward compatibility alias for _parse_llm_response."""
        parsed = self._parse_llm_response(raw)
        return parsed["hypotheses"]

    def _parse_llm_response(self, raw: str) -> dict:
        """Parse LLM response and return structured data with status, follow_up_question, and hypotheses."""
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise DiagnosticServiceError(f"LLM returned invalid JSON: {exc}") from exc

        if not isinstance(data, dict) or "hypotheses" not in data:
            raise DiagnosticServiceError("LLM response missing 'hypotheses' key")

        # Support both old format (without status) and new format (with status)
        status = data.get("status", "complete")
        if status not in ("complete", "needs_more_information"):
            raise DiagnosticServiceError(f"Invalid status value: {status}")

        follow_up_question = data.get("follow_up_question")
        follow_up_reason = data.get("follow_up_reason")

        raw_hypotheses = data["hypotheses"]
        if not isinstance(raw_hypotheses, list):
            raise DiagnosticServiceError("LLM 'hypotheses' must be an array")

        hypotheses: list[DiagnosticHypothesis] = []
        for idx, item in enumerate(raw_hypotheses):
            if not isinstance(item, dict):
                continue
            sanitized = dict(item)
            sanitized.pop("knowledge_references", None)
            sanitized["supporting_evidence"] = self._coerce_string_list(
                sanitized.get("supporting_evidence")
            )
            sanitized["recommended_checks"] = self._coerce_string_list(
                sanitized.get("recommended_checks")
            )
            # Handle new evidence_references field
            if "evidence_references" in sanitized:
                raw_refs = sanitized.pop("evidence_references")
                if isinstance(raw_refs, list):
                    evidence_refs = []
                    for ref_data in raw_refs:
                        if isinstance(ref_data, dict):
                            try:
                                evidence_refs.append(EvidenceReference(**ref_data))
                            except ValidationError:
                                pass  # Skip invalid references
                    sanitized["evidence_references"] = evidence_refs
            if "differential_rank" in sanitized:
                sanitized["differential_rank"] = sanitized.get("differential_rank")
            try:
                hypotheses.append(DiagnosticHypothesis(**sanitized))
            except ValidationError as exc:
                raise DiagnosticServiceError(
                    f"Invalid hypothesis at index {idx}: {exc}"
                ) from exc

        return {
            "status": status,
            "follow_up_question": follow_up_question,
            "follow_up_reason": follow_up_reason,
            "hypotheses": hypotheses,
        }

    def analyze(
        self, db: Session, request: DiagnosticAnalyzeRequest, session: models.DiagnosticSession | None = None
    ) -> DiagnosticAnalyzeResponse:
        # Set up session_db for conversation context methods
        self._session_db = db

        is_new_session = session is None
        is_follow_up = session is not None and request.follow_up_answer is not None

        # Build session context from previous diagnostic results
        session_context = ""
        if session is not None:
            session_context = self._build_session_context(session, request.follow_up_answer)

        # Build conversation context from persisted messages
        conversation_context = ""
        if session is not None:
            conversation_context = self._build_conversation_context(session)

        # Determine turn index for persistence
        turn_index = 0
        if session is not None:
            turn_index = self._get_next_turn_index(session)

        # For follow-up requests, persist user message immediately (session exists)
        user_message_content = ""
        if is_follow_up:
            user_message_content = request.follow_up_answer or ""
            if user_message_content:
                self._persist_user_message(db, session.id, user_message_content, turn_index)
                turn_index += 1

        # Check follow-up turn limit for existing sessions
        if session is not None and not is_new_session:
            follow_up_count = self._count_follow_up_turns(session)
            max_follow_ups = self._settings.diagnostic_max_follow_up_turns
            if follow_up_count >= max_follow_ups:
                # Force final diagnosis - modify request to indicate no more follow-ups allowed
                session_context += f"\n\nNOTE: Maximum follow-up turns ({max_follow_ups}) reached. Provide final diagnosis based on available information."

        query = self._build_search_query(request)
        if session_context:
            query = f"{session_context}\n\n{query}"

        if self._settings.embedding_enabled:
            try:
                query_embedding = self._embedding_service.embed_query(query)
            except Exception:
                query_embedding = None
        else:
            query_embedding = None

        # Extract component IDs from DTC codes and symptoms for retrieval boost
        request_components: list[str] = []
        if request.dtc_codes:
            for dtc in request.dtc_codes:
                component = map_knowledge_entry(dtc, "dtc")
                if component:
                    request_components.append(component.component_id)

        rows = hybrid_search_knowledge_entries(
            db,
            query_embedding=query_embedding,
            query_text=query,
            top_k=10,
            request_components=request_components,
        )

        historical_cases = []
        if query_embedding is not None:
            try:
                historical_cases = search_confirmed_cases(
                    db,
                    query_embedding=query_embedding,
                    query_text=query,
                    top_k=5,
                    make=request.make,
                    model=request.model,
                    year=request.year,
                )
            except Exception:
                historical_cases = []

        evidence = [
            KnowledgeSearchResult(
                id=entry.id,
                category=entry.category,
                entry_key=entry.entry_key,
                content=entry.content,
                source=entry.source,
                similarity_score=round(float(score), 4),
            )
            for entry, score in rows
        ]

        prompt = self._build_prompt(request, evidence, historical_cases=historical_cases, session_context=session_context, conversation_context=conversation_context)
        response_schema = {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["complete", "needs_more_information"]
                },
                "follow_up_question": {
                    "type": ["string", "null"]
                },
                "follow_up_reason": {
                    "type": ["string", "null"]
                },
                "hypotheses": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "fault_description": {
                                "type": "string"
                            },
                            "confidence_score": {
                                "type": "number"
                            },
                            "severity": {
                                "type": "string",
                                "enum": ["low", "medium", "high", "critical"]
                            },
                            "supporting_evidence": {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                }
                            },
                            "recommended_checks": {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                }
                            },
                            "repair_suggestion": {
                                "type": ["string", "null"]
                            },
                            "evidence_references": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "evidence_id": {
                                            "type": "string",
                                            "format": "uuid"
                                        },
                                        "category": {
                                            "type": "string"
                                        },
                                        "entry_key": {
                                            "type": ["string", "null"]
                                        },
                                        "excerpt": {
                                            "type": "string"
                                        },
                                        "similarity_score": {
                                            "type": "number"
                                        },
                                        "relevance": {
                                            "type": "string",
                                            "enum": [
                                                "supporting",
                                                "conflicting",
                                                "contextual"
                                            ]
                                        }
                                    },
                                    "required": [
                                        "evidence_id",
                                        "category",
                                        "entry_key",
                                        "excerpt",
                                        "similarity_score",
                                        "relevance"
                                    ],
                                    "additionalProperties": False
                                }
                            },
                            "differential_rank": {
                                "type": ["integer", "null"]
                            }
                        },
                        "required": [
                            "fault_description",
                            "confidence_score",
                            "severity",
                            "supporting_evidence",
                            "recommended_checks",
                            "repair_suggestion",
                            "evidence_references",
                            "differential_rank"
                        ],
                        "additionalProperties": False
                    }
                }
            },
            "required": [
                "status",
                "follow_up_question",
                "follow_up_reason",
                "hypotheses"
            ],
            "additionalProperties": False
        }
        try:
            raw_response = self._llm_service.complete(prompt, response_schema=response_schema)
        except LLMProviderError as exc:
            raise DiagnosticServiceError(str(exc)) from exc

        parsed = self._parse_llm_response(raw_response)
        status = parsed["status"]
        follow_up_question = parsed.get("follow_up_question")
        follow_up_reason = parsed.get("follow_up_reason")
        parsed_hypotheses = parsed["hypotheses"]

        if is_new_session:
            session_in = DiagnosticSessionCreate(
                vin=request.vin,
                make=request.make,
                model=request.model,
                year=request.year,
                symptom_text=request.symptom_text,
                dtc_codes=request.dtc_codes_text(),
                vehicle_type=request.vehicle_type,
            )
            session = create_diagnostic_session(db, session_in)
            # Persist initial user message with correct session ID
            if request.symptom_text:
                self._persist_user_message(db, session.id, request.symptom_text, 0)
                turn_index = 1

        # Process each hypothesis: validate evidence, build evidence references, calibrate confidence
        hypotheses: list[DiagnosticHypothesis] = []
        for hypothesis in parsed_hypotheses:
            # Validate string-based supporting evidence (backward compatibility)
            validated_evidence, knowledge_refs = self._validate_evidence(hypothesis, evidence)

            # Validate structured evidence references from LLM
            if hypothesis.evidence_references:
                validated_refs = self._validate_evidence_references(hypothesis.evidence_references, evidence)
                hypothesis.evidence_references = validated_refs
                # Also extract knowledge refs from validated structured references
                for ref in validated_refs:
                    if ref.evidence_id not in knowledge_refs:
                        knowledge_refs.append(ref.evidence_id)

            # If no structured references but we have validated string evidence, build them
            if not hypothesis.evidence_references and knowledge_refs:
                hypothesis.evidence_references = self._build_evidence_references(knowledge_refs, evidence)

            component = map_fault_description(hypothesis.fault_description)
            if component is None:
                component = map_evidence_to_component(evidence)

            safety_decision = determine_repair_safety_tier(
                component_id=component.component_id if component else None,
                system_category=component.system_category if component else None,
                severity=hypothesis.severity,
                repair_suggestion=hypothesis.repair_suggestion,
            )

            validated_hypothesis = DiagnosticHypothesis(
                fault_description=hypothesis.fault_description,
                confidence_score=hypothesis.confidence_score,
                severity=hypothesis.severity,
                supporting_evidence=validated_evidence,
                recommended_checks=hypothesis.recommended_checks,
                repair_suggestion=hypothesis.repair_suggestion,
                knowledge_references=knowledge_refs,
                component_id=component.component_id if component else None,
                system_category=component.system_category if component else None,
                vehicle_region=component.vehicle_region if component else None,
                safety_tier=safety_decision.tier.value,
                safety_tier_label=safety_decision.label,
                safety_tier_description=safety_decision.description,
                safety_tier_reasoning=safety_decision.reasoning,
                evidence_references=hypothesis.evidence_references,
                differential_rank=hypothesis.differential_rank,
            )
            hypotheses.append(validated_hypothesis)

        # Detect conflicting evidence across hypotheses
        conflicting_map = self._detect_conflicting_evidence(hypotheses, evidence)
        for idx, hypothesis in enumerate(hypotheses):
            hypothesis._conflicting_count = sum(1 for indices in conflicting_map.values() if idx in indices)

        # Assess evidence quality for each hypothesis
        for hypothesis in hypotheses:
            hypothesis.evidence_quality = self._assess_evidence_quality(hypothesis, evidence)

        # Calibrate confidence for each hypothesis
        for hypothesis in hypotheses:
            calibrated = self._calibrate_confidence(
                hypothesis.confidence_score, hypothesis, evidence, request
            )
            hypothesis.confidence_score = calibrated

        # Rank differential diagnosis
        hypotheses = self._rank_differential(hypotheses, evidence)

        # Determine if follow-up is needed (override LLM if evidence suggests it)
        should_follow_up, auto_question, auto_reason = self._should_request_follow_up(hypotheses, evidence, request)
        if should_follow_up and status == "complete":
            # Evidence suggests we need more info even if LLM said complete
            status = "needs_more_information"
            follow_up_question = auto_question
            follow_up_reason = auto_reason

        # Persist assistant message if there's a follow-up question
        if follow_up_question:
            assistant_content = follow_up_question
            if follow_up_reason:
                assistant_content += f" (Reason: {follow_up_reason})"
            self._persist_assistant_message(db, session.id, assistant_content, turn_index)
            turn_index += 1
        else:
            # Final diagnosis - persist a summary
            summary = f"Diagnosis complete. {len(hypotheses)} hypotheses generated."
            self._persist_assistant_message(db, session.id, summary, turn_index)

        # Persist diagnostic results
        for hypothesis in hypotheses:
            result_in = DiagnosticResultCreate(
                fault_description=hypothesis.fault_description,
                confidence_score=hypothesis.confidence_score,
                severity=hypothesis.severity,
                repair_suggestion=hypothesis.repair_suggestion,
                recommended_checks=hypothesis.recommended_checks,
                supporting_evidence=hypothesis.supporting_evidence,
                knowledge_references=hypothesis.knowledge_references,
            )
            create_diagnostic_result(db, session.id, result_in)

        return DiagnosticAnalyzeResponse(
            session_id=session.id,
            vehicle={
                "vin": request.vin,
                "make": request.make,
                "model": request.model,
                "year": request.year,
                "vehicle_type": request.vehicle_type,
            },
            query=query,
            evidence=evidence,
            hypotheses=hypotheses,
            status=status,
            follow_up_question=follow_up_question,
            follow_up_reason=follow_up_reason,
        )

    def create_confirmed_case_from_result(
        self,
        db: Session,
        session: models.DiagnosticSession,
        result: models.DiagnosticResult,
        confirmed_fault: str,
        confirmed_fault_description: str | None = None,
        repair_suggestion: str | None = None,
        severity: str | None = None,
    ) -> models.ConfirmedDiagnosticCase:
        case_text = (
            f"Vehicle: {session.make or 'Unknown'} {session.model or ''} {session.year or ''}\n"
            f"Symptoms: {session.symptom_text}\n"
            f"DTCs: {session.dtc_codes or 'None'}\n"
            f"Confirmed fault: {confirmed_fault}\n"
        )
        if confirmed_fault_description:
            case_text += f"Description: {confirmed_fault_description}\n"
        if severity:
            case_text += f"Severity: {severity}\n"
        if repair_suggestion:
            case_text += f"Repair: {repair_suggestion}\n"

        embedding: list[float] | None = None
        if self._settings.embedding_enabled:
            try:
                embedding = self._embedding_service.embed_query(case_text)
            except Exception:
                embedding = None

        from app.schemas import ConfirmedDiagnosticCaseCreate

        case_in = ConfirmedDiagnosticCaseCreate(
            make=session.make,
            model=session.model,
            year=session.year,
            vin=session.vin,
            symptom_text=session.symptom_text,
            dtc_codes=session.dtc_codes,
            confirmed_fault=confirmed_fault,
            confirmed_fault_description=confirmed_fault_description,
            repair_suggestion=repair_suggestion,
            severity=severity,
            case_text=case_text,
            embedding=embedding,
            source_session_id=session.id,
            source_result_id=result.id,
            is_verified=True,
        )
        return create_confirmed_case(db, case_in)


def get_diagnostic_service(
    embedding_service: EmbeddingService,
    llm_service: LLMService,
) -> DiagnosticService:
    return DiagnosticService(settings, embedding_service, llm_service)