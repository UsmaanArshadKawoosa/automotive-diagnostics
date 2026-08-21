import json
import uuid
from typing import Any

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.config import Settings, settings
from app.crud import create_diagnostic_result, create_diagnostic_session, hybrid_search_knowledge_entries
from app.db import models
from app.db.database import engine
from app.schemas import (
    DiagnosticAnalyzeRequest,
    DiagnosticAnalyzeResponse,
    DiagnosticHypothesis,
    DiagnosticResultCreate,
    DiagnosticSessionCreate,
    KnowledgeSearchResult,
)
from app.services.component_taxonomy import (
    map_evidence_to_component,
    map_fault_description,
)
from app.services.embeddings import EmbeddingService
from app.services.llm import LLMProviderError, LLMService
from app.services.repair_safety import RepairSafetyTier, determine_repair_safety_tier, SafetyTierDecision


class DiagnosticServiceError(Exception):
    pass


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

    def _format_evidence(self, evidence: list[KnowledgeSearchResult]) -> str:
        lines: list[str] = []
        for idx, item in enumerate(evidence, start=1):
            lines.append(
                f"{idx}. [{item.category}] {item.entry_key or 'n/a'} "
                f"(similarity {item.similarity_score}): {item.content}"
            )
        return "\n".join(lines) if lines else "No relevant knowledge entries were retrieved."

    def _build_prompt(
        self,
        request: DiagnosticAnalyzeRequest,
        evidence: list[KnowledgeSearchResult],
        session_context: str = "",
    ) -> str:
        query = self._build_search_query(request)
        vehicle = " ".join(
            p for p in [request.make, request.model, str(request.year) if request.year else None] if p
        ) or "Unknown vehicle"
        dtcs = ", ".join(request.dtc_codes) if request.dtc_codes else "None provided"

        context_section = ""
        if session_context:
            context_section = f"""
PREVIOUS SESSION CONTEXT
{session_context}

Notes:
- The hypotheses above are prior possibilities, not confirmed facts.
- Focus on the current symptoms and evidence. Do not assume prior hypotheses are correct.
- If the current symptoms suggest a different cause than previously hypothesized, say so.

"""

return f"""You are an expert automotive diagnostic assistant.

Analyze the following case and produce structured diagnostic reasoning.

Vehicle: {vehicle}
DTC codes: {dtcs}
Symptoms: {request.symptom_text}
{context_section}Retrieved knowledge evidence:
{self._format_evidence(evidence)}

Instructions:
- Use ONLY the retrieved evidence above as supporting facts. Do not invent automotive knowledge.
- If evidence is insufficient, clearly state uncertainty and recommend checks before repair.
- Each hypothesis must include a confidence score between 0 and 1 that reflects the available evidence.
- Severity must be one of: low, medium, high, critical.
- Provide concrete recommended checks a technician should perform.
- Provide a repair suggestion only when the evidence reasonably supports it.
- If more information is needed from the user to narrow down the diagnosis, set "needs_more_information" to true and provide a specific follow-up question with reasoning.
- The follow-up question should be specific and actionable for a vehicle owner.

Return a single JSON object with this schema:
{
  "status": "complete" | "needs_more_information",
  "follow_up_question": "string or null",
  "follow_up_reason": "string or null",
  "hypotheses": [
    {
      "fault_description": "string",
      "confidence_score": 0.0,
      "severity": "low|medium|high|critical",
      "supporting_evidence": ["string"],
      "recommended_checks": ["string"],
      "repair_suggestion": "string or null"
    }
  ]
}
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

    def _parse_llm_response(self, raw: str) -> dict:
        """Parse LLM response and return structured data with status, follow_up_question, and hypotheses."""
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise DiagnosticServiceError(f"LLM returned invalid JSON: {exc}") from exc

        if not isinstance(data, dict) or "hypotheses" not in data:
            raise DiagnosticServiceError("LLM response missing 'hypotheses' key")

        if "status" not in data:
            raise DiagnosticServiceError("LLM response missing 'status' key")

        status = data["status"]
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
            # Knowledge references are derived from retrieved evidence, never from the LLM.
            sanitized.pop("knowledge_references", None)
            sanitized["supporting_evidence"] = self._coerce_string_list(
                sanitized.get("supporting_evidence")
            )
            sanitized["recommended_checks"] = self._coerce_string_list(
                sanitized.get("recommended_checks")
            )
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

    def analyze(
        self, db: Session, request: DiagnosticAnalyzeRequest, session: models.DiagnosticSession | None = None
    ) -> DiagnosticAnalyzeResponse:
        session_context = ""
        if session is not None:
            session_context = self._build_session_context(session, request.follow_up_answer)

        query = self._build_search_query(request)
        if session_context:
            query = f"{session_context}\n\n{query}"

        query_embedding = self._embedding_service.embed_query(query)

        rows = hybrid_search_knowledge_entries(db, query_embedding=query_embedding, query_text=query, top_k=10)
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

prompt = self._build_prompt(request, evidence, session_context=session_context)
        response_schema = {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["complete", "needs_more_information"]},
                "follow_up_question": {"type": ["string", "null"]},
                "follow_up_reason": {"type": ["string", "null"]},
                "hypotheses": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "fault_description": {"type": "string"},
                            "confidence_score": {"type": "number"},
                            "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                            "supporting_evidence": {"type": "array", "items": {"type": "string"}},
                            "recommended_checks": {"type": "array", "items": {"type": "string"}},
                            "repair_suggestion": {"type": ["string", "null"]},
                        },
                        "required": [
                            "fault_description",
                            "confidence_score",
                            "severity",
                            "supporting_evidence",
                            "recommended_checks",
                        ],
                    },
                },
            },
            "required": ["status", "hypotheses"],
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

        if session is None:
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

        hypotheses: list[DiagnosticHypothesis] = []
        for hypothesis in parsed_hypotheses:
            validated_evidence, knowledge_refs = self._validate_evidence(hypothesis, evidence)

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
            )
            hypotheses.append(validated_hypothesis)

            result_in = DiagnosticResultCreate(
                fault_description=validated_hypothesis.fault_description,
                confidence_score=validated_hypothesis.confidence_score,
                severity=validated_hypothesis.severity,
                repair_suggestion=validated_hypothesis.repair_suggestion,
                recommended_checks=validated_hypothesis.recommended_checks,
                supporting_evidence=validated_hypothesis.supporting_evidence,
                knowledge_references=validated_hypothesis.knowledge_references,
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
        )


def get_diagnostic_service(
    embedding_service: EmbeddingService,
    llm_service: LLMService,
) -> DiagnosticService:
    return DiagnosticService(settings, embedding_service, llm_service)
