import json
import uuid
from typing import Any

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.config import Settings, settings
from app.crud import create_diagnostic_result, create_diagnostic_session, search_knowledge_entries
from app.db.database import engine
from app.schemas import (
    DiagnosticAnalyzeRequest,
    DiagnosticAnalyzeResponse,
    DiagnosticHypothesis,
    DiagnosticResultCreate,
    DiagnosticSessionCreate,
    KnowledgeSearchResult,
)
from app.services.embeddings import EmbeddingService
from app.services.llm import LLMProviderError, LLMService


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
        parts: list[str] = [request.symptom_text]
        if request.dtc_codes:
            parts.append("DTC codes: " + ", ".join(request.dtc_codes))
        if request.make or request.model:
            vehicle = " ".join(p for p in [request.make, request.model, str(request.year) if request.year else None] if p)
            parts.append(f"Vehicle: {vehicle}")
        return " ".join(parts)

    def _format_evidence(self, evidence: list[KnowledgeSearchResult]) -> str:
        lines: list[str] = []
        for idx, item in enumerate(evidence, start=1):
            lines.append(
                f"{idx}. [{item.category}] {item.entry_key or 'n/a'} "
                f"(similarity {item.similarity_score}): {item.content}"
            )
        return "\n".join(lines) if lines else "No relevant knowledge entries were retrieved."

    def _build_prompt(self, request: DiagnosticAnalyzeRequest, evidence: list[KnowledgeSearchResult]) -> str:
        query = self._build_search_query(request)
        vehicle = " ".join(
            p for p in [request.make, request.model, str(request.year) if request.year else None] if p
        ) or "Unknown vehicle"
        dtcs = ", ".join(request.dtc_codes) if request.dtc_codes else "None provided"

        return f"""You are an expert automotive diagnostic assistant.

Analyze the following case and produce structured diagnostic hypotheses.

Vehicle: {vehicle}
DTC codes: {dtcs}
Symptoms: {request.symptom_text}

Retrieved knowledge evidence:
{self._format_evidence(evidence)}

Instructions:
- Use ONLY the retrieved evidence above as supporting facts. Do not invent automotive knowledge.
- If evidence is insufficient, clearly state uncertainty and recommend checks before repair.
- Each hypothesis must include a confidence score between 0 and 1 that reflects the available evidence.
- Severity must be one of: low, medium, high, critical.
- Provide concrete recommended checks a technician should perform.
- Provide a repair suggestion only when the evidence reasonably supports it.

Return a single JSON object with a "hypotheses" array. Each item must match this schema:
{{
  "hypotheses": [
    {{
      "fault_description": "string",
      "confidence_score": 0.0,
      "severity": "low|medium|high|critical",
      "supporting_evidence": ["string"],
      "recommended_checks": ["string"],
      "repair_suggestion": "string or null"
    }}
  ]
}}
"""

    def _parse_hypotheses(self, raw: str) -> list[DiagnosticHypothesis]:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise DiagnosticServiceError(f"LLM returned invalid JSON: {exc}") from exc

        if not isinstance(data, dict) or "hypotheses" not in data:
            raise DiagnosticServiceError("LLM response missing 'hypotheses' key")

        hypotheses: list[DiagnosticHypothesis] = []
        for idx, item in enumerate(data["hypotheses"]):
            try:
                hypotheses.append(DiagnosticHypothesis(**item))
            except ValidationError as exc:
                raise DiagnosticServiceError(
                    f"Invalid hypothesis at index {idx}: {exc}"
                ) from exc
        return hypotheses

    def analyze(self, db: Session, request: DiagnosticAnalyzeRequest) -> DiagnosticAnalyzeResponse:
        query = self._build_search_query(request)
        query_embedding = self._embedding_service.embed_query(query)

        rows = search_knowledge_entries(db, query_embedding=query_embedding, top_k=8)
        evidence = [
            KnowledgeSearchResult(
                id=entry.id,
                category=entry.category,
                entry_key=entry.entry_key,
                content=entry.content,
                source=entry.source,
                similarity_score=round(1.0 - float(distance), 4),
            )
            for entry, distance in rows
        ]

        prompt = self._build_prompt(request, evidence)
        response_schema = {
            "type": "object",
            "properties": {
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
                }
            },
            "required": ["hypotheses"],
        }

        try:
            raw_response = self._llm_service.complete(prompt, response_schema=response_schema)
        except LLMProviderError as exc:
            raise DiagnosticServiceError(str(exc)) from exc

        hypotheses = self._parse_hypotheses(raw_response)

        session_in = DiagnosticSessionCreate(
            vin=request.vin,
            make=request.make,
            model=request.model,
            year=request.year,
            symptom_text=request.symptom_text,
            dtc_codes=request.dtc_codes_text(),
        )
        session = create_diagnostic_session(db, session_in)

        for hypothesis in hypotheses:
            result_in = DiagnosticResultCreate(
                fault_description=hypothesis.fault_description,
                confidence_score=hypothesis.confidence_score,
                severity=hypothesis.severity,
                repair_suggestion=hypothesis.repair_suggestion,
            )
            create_diagnostic_result(db, session.id, result_in)

        return DiagnosticAnalyzeResponse(
            session_id=session.id,
            vehicle={
                "vin": request.vin,
                "make": request.make,
                "model": request.model,
                "year": request.year,
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
