"""
Mock LLM Provider for deterministic evaluation.

This provider allows configuring different responses for different benchmark cases
without requiring a live Ollama instance. It parses the evidence catalog from the
prompt to include valid evidence references.
"""
import json
import re
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
    """LLM Provider that returns case-specific responses based on the benchmark case.

    Dynamically extracts evidence IDs from the prompt's evidence catalog and includes
    them in the response for proper evidence validation.
    """

    def __init__(self, case_responses: dict[str, dict]) -> None:
        """
        Initialize with case-specific response configurations.

        Args:
            case_responses: Dictionary mapping case_id to response configuration dict
                           containing keys: fault_description, confidence_score, severity,
                           supporting_evidence, recommended_checks, repair_suggestion,
                           status, follow_up_question, follow_up_reason
        """
        self._case_responses = case_responses
        self._current_case_id = None

    def set_current_case(self, case_id: str) -> None:
        """Set the current case ID for response selection."""
        self._current_case_id = case_id

    def complete(self, prompt: str, response_schema: dict[str, Any] | None = None) -> str:
        """Return the response configured for the current case, with evidence references."""
        if not self._current_case_id or self._current_case_id not in self._case_responses:
            return self._fallback_response()

        case_config = self._case_responses[self._current_case_id].copy()

        # Parse evidence catalog from prompt to get evidence IDs
        evidence_catalog = self._parse_evidence_catalog(prompt)

        # Build evidence references for the hypothesis
        evidence_refs = self._build_evidence_references(case_config, evidence_catalog)

        # Convert evidence_refs to dict with string UUIDs for JSON serialization
        evidence_refs_dict = []
        for ref in evidence_refs:
            ref_dict = ref.model_dump()
            ref_dict['evidence_id'] = str(ref_dict['evidence_id'])
            evidence_refs_dict.append(ref_dict)

        response = {
            "status": case_config.get("status", "complete"),
            "follow_up_question": case_config.get("follow_up_question"),
            "follow_up_reason": case_config.get("follow_up_reason"),
            "hypotheses": [{
                "fault_description": case_config.get("fault_description", "Unknown fault"),
                "confidence_score": case_config.get("confidence_score", 0.7),
                "severity": case_config.get("severity", "medium"),
                "supporting_evidence": case_config.get("supporting_evidence", []),
                "recommended_checks": case_config.get("recommended_checks", []),
                "repair_suggestion": case_config.get("repair_suggestion"),
                "evidence_references": evidence_refs_dict,
                "differential_rank": 1,
            }],
        }

        return json.dumps(response)

    def _parse_evidence_catalog(self, prompt: str) -> dict[str, dict]:
        """Parse the evidence catalog section from the prompt.

        Returns a mapping of entry_key -> {evidence_id, category, entry_key, similarity_score, content}
        """
        catalog: dict[str, dict] = {}

        # Find the EVIDENCE CATALOG section
        catalog_match = re.search(r'EVIDENCE CATALOG \(reference these by evidence_id in your response\):(.*?)(?:\n\n|\nInstructions:|$)', prompt, re.DOTALL)
        if not catalog_match:
            return catalog

        catalog_text = catalog_match.group(1)

        # Parse each evidence line
        # Format: "  evidence_id: <uuid> | category: <cat> | entry_key: <key> | similarity: <score> | content: <text>"
        for line in catalog_text.strip().split('\n'):
            line = line.strip()
            if not line or not line.startswith('evidence_id:'):
                continue

            # Parse the line
            parts = {}
            for part in line.split('|'):
                part = part.strip()
                if ':' in part:
                    key, value = part.split(':', 1)
                    parts[key.strip()] = value.strip()

            if 'evidence_id' in parts and 'entry_key' in parts:
                entry_key = parts['entry_key']
                catalog[entry_key] = {
                    'evidence_id': parts['evidence_id'],
                    'category': parts.get('category', ''),
                    'entry_key': entry_key,
                    'similarity_score': float(parts.get('similarity', 0.0)),
                    'content': parts.get('content', ''),
                }

        return catalog

    def _build_evidence_references(self, case_config: dict, evidence_catalog: dict[str, dict]) -> list[EvidenceReference]:
        """Build evidence references matching the case's expected evidence category."""
        evidence_refs: list[EvidenceReference] = []
        expected_category = case_config.get("expected_evidence_category")
        expected_entry_key = case_config.get("expected_entry_key")

        # Determine which evidence to reference
        target_entries: list[dict] = []

        if expected_entry_key and expected_entry_key in evidence_catalog:
            # Reference specific entry
            target_entries.append(evidence_catalog[expected_entry_key])
        elif expected_category:
            # Reference all entries matching the category
            for entry in evidence_catalog.values():
                if entry['category'] == expected_category:
                    target_entries.append(entry)
        else:
            # Reference all available evidence (up to 3)
            target_entries = list(evidence_catalog.values())[:3]

        # Build EvidenceReference objects
        for entry in target_entries:
            try:
                ref = EvidenceReference(
                    evidence_id=entry['evidence_id'],
                    category=entry['category'],
                    entry_key=entry['entry_key'],
                    excerpt=entry['content'][:200],
                    similarity_score=entry['similarity_score'],
                    relevance="supporting",
                )
                evidence_refs.append(ref)
            except Exception:
                pass  # Skip invalid entries

        return evidence_refs

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