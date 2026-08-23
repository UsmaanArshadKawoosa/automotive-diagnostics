"""
Mock LLM Provider for deterministic evaluation.

This provider allows configuring different responses for different benchmark cases
without requiring a live Ollama instance.
"""
import json
from typing import Any

from app.schemas import DiagnosticHypothesis, EvidenceReference
from app.services.llm import LLMProvider


class EvaluationLLMProvider(LLMProvider):
    """LLM Provider that returns pre-configured responses for evaluation."""

    def __init__(self, responses: dict[str, str] | None = None) -> None:
        """
        Initialize with a mapping of case_id -> JSON response string.

        Args:
            responses: Dictionary mapping case identifiers to expected LLM responses.
        """
        self._responses = responses or {}
        self._call_count = 0

    def set_response(self, case_id: str, response: str) -> None:
        """Set a specific response for a case."""
        self._responses[case_id] = response

    def complete(self, prompt: str, response_schema: dict[str, Any] | None = None) -> str:
        """Return the configured response for the current case."""
        self._call_count += 1
        # For evaluation, we use a default response if no specific one is configured
        # The case_id would need to be extracted from the prompt or passed via context
        return self._responses.get("default", self._default_response())

    def _default_response(self) -> str:
        """Generate a minimal valid response for cases without specific configuration."""
        hypothesis = DiagnosticHypothesis(
            fault_description="Unknown fault",
            confidence_score=0.5,
            severity="medium",
            supporting_evidence=["Insufficient information"],
            recommended_checks=["Gather more information"],
            repair_suggestion=None,
            evidence_references=[],
            differential_rank=1,
        )
        return json.dumps({
            "status": "needs_more_information",
            "follow_up_question": "Can you provide more details about the symptoms?",
            "follow_up_reason": "Insufficient information for diagnosis",
            "hypotheses": [hypothesis.model_dump()]
        })


class CaseSpecificLLMProvider(LLMProvider):
    """LLM Provider that returns case-specific responses based on the benchmark case."""

    def __init__(self, case_responses: dict[str, dict]) -> None:
        """
        Initialize with case-specific response configurations.

        Args:
            case_responses: Dictionary mapping case_id to response configuration dict
                           containing keys: fault_description, confidence_score, severity,
                           supporting_evidence, recommended_checks, repair_suggestion,
                           status, follow_up_question, follow_up_reason, evidence_references
        """
        self._case_responses = case_responses
        self._current_case_id = None

    def set_current_case(self, case_id: str) -> None:
        """Set the current case ID for response selection."""
        self._current_case_id = case_id

    def complete(self, prompt: str, response_schema: dict[str, Any] | None = None) -> str:
        """Return the response configured for the current case."""
        if self._current_case_id and self._current_case_id in self._case_responses:
            return json.dumps(self._case_responses[self._current_case_id])
        # Fallback
        return self._fallback_response()

    def _fallback_response(self) -> str:
        hypothesis = DiagnosticHypothesis(
            fault_description="Unable to determine fault",
            confidence_score=0.3,
            severity="low",
            supporting_evidence=["No specific evidence available"],
            recommended_checks=["Consult professional"],
            repair_suggestion=None,
            evidence_references=[],
            differential_rank=1,
        )
        return json.dumps({
            "status": "needs_more_information",
            "follow_up_question": "Could you describe the symptoms in more detail?",
            "follow_up_reason": "Insufficient information for diagnosis",
            "hypotheses": [hypothesis.model_dump()]
        })