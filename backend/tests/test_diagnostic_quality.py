import json

from app.schemas import DiagnosticAnalyzeRequest, DiagnosticHypothesis
from tests.conftest import FakeEmbeddingService, FakeLLMService


def _make_service() -> "object":
    from app.services.diagnostic import DiagnosticService

    embedding = FakeEmbeddingService()
    return DiagnosticService(embedding._settings, embedding, FakeLLMService())


def test_prompt_requests_multiple_hypotheses_and_conservative_followup():
    service = _make_service()
    request = DiagnosticAnalyzeRequest(symptom_text="My car makes a grinding noise when braking.")
    prompt = service._build_prompt(request, evidence=[])

    # Multiple-hypothesis expectation
    assert "3 to 5" in prompt
    # Conservative follow-up expectation (only when materially changes diagnosis)
    assert "MATERIALLY" in prompt.upper()
    # Confidence should reflect symptom pattern, not just missing vehicle specifics
    assert "characteristic symptom pattern" in prompt
    # Must not encourage vague "provide more information" style blocking
    assert "never a vague request" in prompt


def test_weak_evidence_does_not_force_follow_up():
    service = _make_service()
    hypothesis = DiagnosticHypothesis(
        fault_description="Worn brake pads contacting rotor",
        confidence_score=0.55,
        severity="medium",
        supporting_evidence=[],
        recommended_checks=["Inspect brake pad thickness"],
        repair_suggestion="Replace brake pads and resurface rotor if needed",
        evidence_references=[],
        evidence_quality="weak",
    )
    should_follow_up, question, reason = service._should_request_follow_up(
        [hypothesis], [], DiagnosticAnalyzeRequest(symptom_text="grinding when braking")
    )
    # A weak-evidence preliminary differential must NOT be blocked by a forced question.
    assert should_follow_up is False
    assert question is None


def test_follow_up_still_forced_when_no_hypotheses():
    service = _make_service()
    should_follow_up, question, _ = service._should_request_follow_up(
        [], [], DiagnosticAnalyzeRequest(symptom_text="weird noise")
    )
    assert should_follow_up is True
    assert question is not None


def test_multiple_hypotheses_survive_parse_and_rank():
    service = _make_service()
    raw = json.dumps(
        {
            "status": "complete",
            "follow_up_question": None,
            "follow_up_reason": None,
            "hypotheses": [
                {
                    "fault_description": "Severely worn brake pads",
                    "confidence_score": 0.62,
                    "severity": "high",
                    "supporting_evidence": ["Pad material worn below minimum"],
                    "recommended_checks": ["Inspect pad thickness"],
                    "repair_suggestion": "Replace pads",
                    "evidence_references": [],
                    "differential_rank": 1,
                },
                {
                    "fault_description": "Scored brake rotor",
                    "confidence_score": 0.34,
                    "severity": "medium",
                    "supporting_evidence": ["Rotor surface damage"],
                    "recommended_checks": ["Measure rotor runout"],
                    "repair_suggestion": "Resurface or replace rotor",
                    "evidence_references": [],
                    "differential_rank": 2,
                },
                {
                    "fault_description": "Sticking caliper",
                    "confidence_score": 0.18,
                    "severity": "low",
                    "supporting_evidence": ["Uneven pad wear"],
                    "recommended_checks": ["Check caliper slide movement"],
                    "repair_suggestion": "Service caliper",
                    "evidence_references": [],
                    "differential_rank": 3,
                },
            ],
        }
    )
    parsed = service._parse_llm_response(raw)
    assert len(parsed["hypotheses"]) == 3
    ranked = service._rank_differential(parsed["hypotheses"], [])
    assert [h.differential_rank for h in ranked] == [1, 2, 3]
    # Ranking preserves descending confidence order
    assert ranked[0].confidence_score >= ranked[1].confidence_score >= ranked[2].confidence_score


def test_null_diy_repair_and_null_difficulty_parse_without_error():
    service = _make_service()
    raw = json.dumps(
        {
            "status": "complete",
            "follow_up_question": None,
            "follow_up_reason": None,
            "hypotheses": [
                {
                    "fault_description": "Brake issue",
                    "confidence_score": 0.5,
                    "severity": "high",
                    "supporting_evidence": [],
                    "recommended_checks": ["Inspect brakes"],
                    "repair_suggestion": None,
                    "evidence_references": [],
                    "differential_rank": 1,
                    "diy_repair": None,
                }
            ],
        }
    )
    parsed = service._parse_llm_response(raw)
    assert parsed["hypotheses"][0].diy_repair is None

    raw_null_difficulty = json.dumps(
        {
            "status": "complete",
            "follow_up_question": None,
            "follow_up_reason": None,
            "hypotheses": [
                {
                    "fault_description": "Brake issue",
                    "confidence_score": 0.5,
                    "severity": "high",
                    "supporting_evidence": [],
                    "recommended_checks": ["Inspect brakes"],
                    "repair_suggestion": None,
                    "evidence_references": [],
                    "differential_rank": 1,
                    "diy_repair": {
                        "suitable": False,
                        "suitability": "Professional recommended",
                        "difficulty": None,
                        "estimated_time": None,
                        "tools": [],
                        "parts": [],
                        "safety_warnings": [],
                        "preparation_steps": [],
                        "steps": [],
                        "verification_steps": [],
                        "professional_help_conditions": [],
                    },
                }
            ],
        }
    )
    parsed2 = service._parse_llm_response(raw_null_difficulty)
    assert parsed2["hypotheses"][0].diy_repair.difficulty is None
    assert parsed2["hypotheses"][0].diy_repair.suitable is False
