"""
Evaluation harness entry point.

Run with: python -m evaluation
"""
import sys
from sqlalchemy.orm import Session
from sqlalchemy import create_engine

from app.config import settings
from app.db.database import engine
from app.services.embeddings import EmbeddingService, get_embedding_service
from app.services.llm import LLMProvider
from tests.benchmark_cases import get_all_cases

from .mock_llm import CaseSpecificLLMProvider
from .runner import DiagnosticEvaluator
from .report import EvaluationReporter, print_failure_breakdown


def build_case_responses() -> dict[str, dict]:
    """Build case-specific LLM responses for deterministic evaluation.

    Returns a mapping of case_id -> response dict compatible with the LLM response schema.
    Fault descriptions must match FAULT_DESCRIPTION_PREFIXES in component_taxonomy.py.
    """
    return {
        "B001": {
            "status": "complete",
            "follow_up_question": None,
            "follow_up_reason": None,
            "fault_description": "Faulty spark plug causing misfire",
            "confidence_score": 0.85,
            "severity": "high",
            "supporting_evidence": ["[dtc] P0300"],
            "recommended_checks": ["Inspect spark plugs", "Check ignition coils"],
            "repair_suggestion": "Replace spark plugs if worn",
            "expected_evidence_category": "dtc",
            "expected_entry_key": "P0300",
        },
        "B002": {
            "status": "complete",
            "follow_up_question": None,
            "follow_up_reason": None,
            "fault_description": "Faulty MAF sensor causing lean condition",
            "confidence_score": 0.8,
            "severity": "medium",
            "supporting_evidence": ["[dtc] P0171"],
            "recommended_checks": ["Clean MAF sensor", "Check for vacuum leaks"],
            "repair_suggestion": "Clean or replace MAF sensor",
            "expected_evidence_category": "dtc",
            "expected_entry_key": "P0171",
        },
        "B003": {
            "status": "complete",
            "follow_up_question": None,
            "follow_up_reason": None,
            "fault_description": "Restricted catalytic converter",
            "confidence_score": 0.8,
            "severity": "high",
            "supporting_evidence": ["[dtc] P0420"],
            "recommended_checks": ["Check exhaust for leaks", "Monitor oxygen sensor readings"],
            "repair_suggestion": "Replace catalytic converter if confirmed",
            "expected_evidence_category": "dtc",
            "expected_entry_key": "P0420",
        },
        "B004": {
            "status": "complete",
            "follow_up_question": None,
            "follow_up_reason": None,
            "fault_description": "Faulty idle air control valve",
            "confidence_score": 0.75,
            "severity": "medium",
            "supporting_evidence": ["[dtc] P0505"],
            "recommended_checks": ["Clean IAC valve", "Check for vacuum leaks"],
            "repair_suggestion": "Clean or replace IAC valve",
            "expected_evidence_category": "dtc",
            "expected_entry_key": "P0505",
        },
        "B005": {
            "status": "complete",
            "follow_up_question": None,
            "follow_up_reason": None,
            "fault_description": "Failed crankshaft position sensor",
            "confidence_score": 0.9,
            "severity": "high",
            "supporting_evidence": ["[dtc] P0335"],
            "recommended_checks": ["Test crankshaft sensor resistance", "Check wiring"],
            "repair_suggestion": "Replace crankshaft position sensor",
            "expected_evidence_category": "dtc",
            "expected_entry_key": "P0335",
        },
        "B006": {
            "status": "needs_more_information",
            "follow_up_question": "Does the rough idle change under specific conditions like load, temperature, or RPM range?",
            "follow_up_reason": "Symptom-only case with weak evidence",
            "fault_description": "Vacuum leak causing rough idle",
            "confidence_score": 0.65,
            "severity": "medium",
            "supporting_evidence": ["[symptom] rough_idle"],
            "recommended_checks": ["Smoke test intake system", "Check vacuum hoses"],
            "repair_suggestion": "Repair vacuum leak",
            "expected_evidence_category": "symptom",
            "expected_entry_key": "rough_idle",
        },
        "B007": {
            "status": "needs_more_information",
            "follow_up_question": "Does the misfire occur only under load/acceleration, or also at idle?",
            "follow_up_reason": "Symptom-only case with weak evidence",
            "fault_description": "Worn spark plug causing misfire",
            "confidence_score": 0.65,
            "severity": "high",
            "supporting_evidence": ["[symptom] engine_misfire"],
            "recommended_checks": ["Inspect spark plugs", "Check ignition coils"],
            "repair_suggestion": "Replace spark plugs",
            "expected_evidence_category": "symptom",
            "expected_entry_key": "engine_misfire",
        },
        "B008": {
            "status": "needs_more_information",
            "follow_up_question": "Can you describe the brake symptoms in more detail? Any fluid leaks or warning lights?",
            "follow_up_reason": "No brake symptom knowledge in knowledge base",
            "fault_description": "Failed master cylinder causing soft brake pedal",
            "confidence_score": 0.5,
            "severity": "critical",
            "supporting_evidence": [],
            "recommended_checks": ["Check brake fluid level", "Inspect for leaks"],
            "repair_suggestion": "Replace master cylinder",
            "expected_evidence_category": "none",
        },
        "B009": {
            "status": "needs_more_information",
            "follow_up_question": "Is there any coolant leak visible? Does the overheating occur at idle or under load?",
            "follow_up_reason": "Symptom-only case with weak evidence",
            "fault_description": "Faulty thermostat causing overheating",
            "confidence_score": 0.65,
            "severity": "critical",
            "supporting_evidence": ["[symptom] engine_overheating"],
            "recommended_checks": ["Check coolant level", "Test thermostat operation"],
            "repair_suggestion": "Replace thermostat",
            "expected_evidence_category": "symptom",
            "expected_entry_key": "engine_overheating",
        },
        "B010": {
            "status": "complete",
            "follow_up_question": None,
            "follow_up_reason": None,
            "fault_description": "Worn spark plug causing misfire and rough idle",
            "confidence_score": 0.85,
            "severity": "high",
            "supporting_evidence": ["[dtc] P0300", "[symptom] rough_idle"],
            "recommended_checks": ["Inspect spark plugs", "Check ignition coils"],
            "repair_suggestion": "Replace spark plugs",
            "expected_evidence_category": "dtc",
            "expected_entry_key": "P0300",
        },
        "B011": {
            "status": "complete",
            "follow_up_question": None,
            "follow_up_reason": None,
            "fault_description": "Faulty MAF sensor causing lean condition and rough idle",
            "confidence_score": 0.8,
            "severity": "medium",
            "supporting_evidence": ["[dtc] P0171", "[symptom] rough_idle"],
            "recommended_checks": ["Clean MAF sensor", "Check for vacuum leaks"],
            "repair_suggestion": "Clean or replace MAF sensor",
            "expected_evidence_category": "dtc",
            "expected_entry_key": "P0171",
        },
        "B012": {
            "status": "complete",
            "follow_up_question": None,
            "follow_up_reason": None,
            "fault_description": "Failed EVAP purge valve",
            "confidence_score": 0.75,
            "severity": "medium",
            "supporting_evidence": ["[dtc] P0442"],
            "recommended_checks": ["Test purge valve operation", "Check EVAP system for leaks"],
            "repair_suggestion": "Replace EVAP purge valve",
            "expected_evidence_category": "dtc",
            "expected_entry_key": "P0442",
        },
        "B013": {
            "status": "needs_more_information",
            "follow_up_question": "Does the rough idle change under specific conditions like load, temperature, or RPM range?",
            "follow_up_reason": "Multiple plausible causes without DTC",
            "fault_description": "Vacuum leak causing rough idle",
            "confidence_score": 0.6,
            "severity": "medium",
            "supporting_evidence": ["[symptom] rough_idle"],
            "recommended_checks": ["Smoke test intake system", "Check vacuum hoses"],
            "repair_suggestion": "Repair vacuum leak",
            "expected_evidence_category": "symptom",
            "expected_entry_key": "rough_idle",
        },
        "B014": {
            "status": "needs_more_information",
            "follow_up_question": "Does the hard start occur only when cold, or also when warm? Any check engine light?",
            "follow_up_reason": "Multiple plausible causes for hard start",
            "fault_description": "Faulty fuel pump causing hard start",
            "confidence_score": 0.6,
            "severity": "medium",
            "supporting_evidence": ["[symptom] hard_start"],
            "recommended_checks": ["Test fuel pressure", "Check fuel pump relay"],
            "repair_suggestion": "Replace fuel pump if pressure low",
            "expected_evidence_category": "symptom",
            "expected_entry_key": "hard_start",
        },
        "B015": {
            "status": "needs_more_information",
            "follow_up_question": "Does the misfire occur only under load/acceleration, or also at idle?",
            "follow_up_reason": "Conflicting evidence between DTC (lean) and symptoms (misfire)",
            "fault_description": "Faulty MAF sensor causing lean condition",
            "confidence_score": 0.65,
            "severity": "medium",
            "supporting_evidence": ["[dtc] P0171"],
            "recommended_checks": ["Clean MAF sensor", "Check for vacuum leaks"],
            "repair_suggestion": "Clean or replace MAF sensor",
            "expected_evidence_category": "dtc",
            "expected_entry_key": "P0171",
        },
        "B016": {
            "status": "needs_more_information",
            "follow_up_question": "Can you describe the symptoms in more detail? (e.g., noises, smells, when it occurs)",
            "follow_up_reason": "Insufficient information for diagnosis",
            "fault_description": "Faulty fuel pump causing poor performance",
            "confidence_score": 0.4,
            "severity": "medium",
            "supporting_evidence": [],
            "recommended_checks": ["Describe symptoms in detail", "Test fuel pressure"],
            "repair_suggestion": None,
            "expected_evidence_category": "symptom",
            "expected_entry_key": "hard_start",
        },
        "B017": {
            "status": "needs_more_information",
            "follow_up_question": "The DTC code P9999 is not recognized. Can you confirm the exact code?",
            "follow_up_reason": "Unknown DTC not in knowledge base",
            "fault_description": "Unknown fault",
            "confidence_score": 0.2,
            "severity": "low",
            "supporting_evidence": [],
            "recommended_checks": ["Confirm DTC code"],
            "repair_suggestion": None,
            "expected_evidence_category": "none",
        },
        "B018": {
            "status": "complete",
            "follow_up_question": None,
            "follow_up_reason": None,
            "fault_description": "Failed vehicle speed sensor",
            "confidence_score": 0.8,
            "severity": "critical",
            "supporting_evidence": ["[dtc] P0500"],
            "recommended_checks": ["Test vehicle speed sensor", "Check ABS module"],
            "repair_suggestion": "Replace vehicle speed sensor",
            "expected_evidence_category": "dtc",
            "expected_entry_key": "P0500",
        },
        "B019": {
            "status": "complete",
            "follow_up_question": None,
            "follow_up_reason": None,
            "fault_description": "Failed brake booster",
            "confidence_score": 0.85,
            "severity": "critical",
            "supporting_evidence": ["[dtc] P0504"],
            "recommended_checks": ["Test brake booster vacuum", "Check for vacuum leaks"],
            "repair_suggestion": "Replace brake booster",
            "expected_evidence_category": "dtc",
            "expected_entry_key": "P0504",
        },
        "B020": {
            "status": "complete",
            "follow_up_question": None,
            "follow_up_reason": None,
            "fault_description": "Faulty spark plug cylinder 1",
            "confidence_score": 0.85,
            "severity": "high",
            "supporting_evidence": ["[dtc] P0301"],
            "recommended_checks": ["Inspect cylinder 1 spark plug", "Check cylinder 1 ignition coil"],
            "repair_suggestion": "Replace cylinder 1 spark plug and coil if needed",
            "expected_evidence_category": "dtc",
            "expected_entry_key": "P0301",
        },
        "B021": {
            "status": "complete",
            "follow_up_question": None,
            "follow_up_reason": None,
            "fault_description": "Faulty fuel injector circuit",
            "confidence_score": 0.8,
            "severity": "medium",
            "supporting_evidence": ["[dtc] P0201"],
            "recommended_checks": ["Test injector resistance", "Check injector wiring"],
            "repair_suggestion": "Replace fuel injector if faulty",
            "expected_evidence_category": "dtc",
            "expected_entry_key": "P0201",
        },
        "B022": {
            "status": "complete",
            "follow_up_question": None,
            "follow_up_reason": None,
            "fault_description": "Faulty thermostat",
            "confidence_score": 0.8,
            "severity": "high",
            "supporting_evidence": ["[dtc] P0125"],
            "recommended_checks": ["Test thermostat operation", "Check coolant temperature sensor"],
            "repair_suggestion": "Replace thermostat",
            "expected_evidence_category": "dtc",
            "expected_entry_key": "P0125",
        },
        "B023": {
            "status": "complete",
            "follow_up_question": None,
            "follow_up_reason": None,
            "fault_description": "Failed EVAP vent valve",
            "confidence_score": 0.75,
            "severity": "medium",
            "supporting_evidence": ["[dtc] P0446"],
            "recommended_checks": ["Test EVAP vent valve", "Check charcoal canister"],
            "repair_suggestion": "Replace EVAP vent valve",
            "expected_evidence_category": "dtc",
            "expected_entry_key": "P0446",
        },
        "B024": {
            "status": "complete",
            "follow_up_question": None,
            "follow_up_reason": None,
            "fault_description": "Failed alternator",
            "confidence_score": 0.8,
            "severity": "medium",
            "supporting_evidence": ["[dtc] P0626"],
            "recommended_checks": ["Test alternator output voltage", "Check voltage regulator"],
            "repair_suggestion": "Replace alternator or voltage regulator",
            "expected_evidence_category": "dtc",
            "expected_entry_key": "P0626",
        },
        "B025": {
            "status": "needs_more_information",
            "follow_up_question": "Does the misfire occur at idle, under load, or randomly? Any other symptoms?",
            "follow_up_reason": "P0300 has multiple root causes - need more info to narrow down",
            "fault_description": "Worn spark plug causing random misfire",
            "confidence_score": 0.65,
            "severity": "high",
            "supporting_evidence": ["[dtc] P0300"],
            "recommended_checks": ["Inspect all spark plugs", "Check ignition coils"],
            "repair_suggestion": "Replace spark plugs if worn",
            "expected_evidence_category": "dtc",
            "expected_entry_key": "P0300",
        },
    }


def main() -> int:
    """Run the full evaluation suite."""
    print("=" * 80)
    print("STARTING DIAGNOSTIC EVALUATION")
    print("=" * 80)
    print()

    # Build case-specific LLM responses
    case_responses = build_case_responses()

    # Create mock LLM provider
    llm_provider = CaseSpecificLLMProvider(case_responses)

    # Create embedding service (real sentence-transformers for compatible retrieval)
    embedding_service = get_embedding_service()

    # Create database session
    db_engine = create_engine(settings.sqlalchemy_database_url, pool_pre_ping=True)
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
    db: Session = SessionLocal()

    try:
        # Create evaluator
        evaluator = DiagnosticEvaluator(
            db=db,
            embedding_service=embedding_service,
            llm_provider=llm_provider,
        )

        # Run all cases
        print("Running benchmark cases...")
        results = evaluator.run_all_cases()

        # Compute aggregate metrics
        aggregate = evaluator.compute_aggregate()

        # Generate report
        reporter = EvaluationReporter(evaluator, aggregate)
        reporter.generate_human_readable(sys.stdout)

        # Print failure breakdown
        print_failure_breakdown(evaluator)

        # Save JSON report
        reporter.save_json("evaluation_report.json")
        print("\nJSON report saved to evaluation_report.json")

        # Return exit code based on results
        if aggregate.failed_cases > 0:
            print(f"\nEVALUATION COMPLETE: {aggregate.failed_cases} cases failed")
            return 1
        else:
            print(f"\nEVALUATION COMPLETE: All {aggregate.passed_cases} cases passed")
            return 0

    finally:
        db.close()
        db_engine.dispose()


if __name__ == "__main__":
    sys.exit(main())