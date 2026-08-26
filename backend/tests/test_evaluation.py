import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.config import Settings, settings
from app.db.database import engine as app_engine
from tests.conftest import FakeEmbeddingService
from app.services.llm import LLMProvider
from tests.benchmark_cases import (
    BenchmarkCase,
    get_all_cases,
    get_case,
    get_cases_by_focus,
    get_cases_expecting_follow_up,
    get_safety_critical_cases,
    get_dtc_only_cases,
    get_symptom_only_cases,
    get_dtc_plus_symptom_cases,
)
from evaluation.mock_llm import CaseSpecificLLMProvider, EvaluationLLMProvider
from evaluation.runner import DiagnosticEvaluator
from evaluation.metrics import (
    CaseEvaluationResult,
    AggregateMetrics,
    MetricResult,
    EvaluationResult,
)


class TestBenchmarkLoading:
    def test_get_all_cases_returns_nonempty(self):
        cases = get_all_cases()
        assert len(cases) == 25

    def test_case_ids_are_unique(self):
        cases = get_all_cases()
        ids = [c.case_id for c in cases]
        assert len(ids) == len(set(ids))

    def test_all_cases_have_required_fields(self):
        cases = get_all_cases()
        for case in cases:
            assert case.case_id
            assert case.description
            assert case.symptom_text
            assert case.expected_component_id
            assert isinstance(case.dtc_codes, list)
            assert isinstance(case.acceptable_alternative_components, list)

    def test_get_case_by_id(self):
        case = get_case("B001")
        assert case is not None
        assert case.case_id == "B001"
        assert case.expected_component_id == "spark_plug"

    def test_get_case_unknown_returns_none(self):
        case = get_case("INVALID")
        assert case is None

    def test_get_cases_by_focus(self):
        dtc_cases = get_cases_by_focus("DTC")
        assert len(dtc_cases) > 0
        for case in dtc_cases:
            assert "dtc" in case.test_focus.lower() or "DTC" in case.test_focus

    def test_get_cases_expecting_follow_up(self):
        cases = get_cases_expecting_follow_up()
        assert len(cases) > 0
        for case in cases:
            assert case.expects_follow_up is True

    def test_get_safety_critical_cases(self):
        cases = get_safety_critical_cases()
        assert len(cases) > 0
        for case in cases:
            assert case.expected_safety_tier == "immediate_professional"

    def test_get_dtc_only_cases(self):
        cases = get_dtc_only_cases()
        for case in cases:
            assert case.dtc_codes
            assert case.symptom_text in ("Check engine light on", "Check engine light on, possible rotten egg smell")

    def test_get_symptom_only_cases(self):
        cases = get_symptom_only_cases()
        for case in cases:
            assert not case.dtc_codes

    def test_get_dtc_plus_symptom_cases(self):
        cases = get_dtc_plus_symptom_cases()
        for case in cases:
            assert case.dtc_codes
            assert case.symptom_text not in ("Check engine light on", "Check engine light on, possible rotten egg smell")


class TestBenchmarkSchemaValidation:
    def test_valid_case_to_request(self):
        case = get_case("B001")
        request = case.to_request()
        assert request.make == "Toyota"
        assert request.model == "Corolla"
        assert request.year == 2020
        assert request.dtc_codes == ["P0300"]
        assert request.symptom_text == "Check engine light on"

    def test_case_without_dtc_codes(self):
        case = get_case("B006")
        request = case.to_request()
        assert request.dtc_codes is None


class TestDeterministicScoring:
    @pytest.fixture
    def evaluator_setup(self):
        db_engine = create_engine(settings.sqlalchemy_database_url, pool_pre_ping=True)
        from sqlalchemy.orm import sessionmaker
        SessionLocal = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
        db = SessionLocal()

        embedding_service = FakeEmbeddingService()

        case_responses = {
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
        }
        llm_provider = CaseSpecificLLMProvider(case_responses)

        evaluator = DiagnosticEvaluator(
            db=db,
            embedding_service=embedding_service,
            llm_provider=llm_provider,
        )

        yield evaluator, db, db_engine

        db.close()
        db_engine.dispose()

    def test_same_case_produces_identical_results(self, evaluator_setup):
        evaluator, db, _ = evaluator_setup

        case = get_case("B001")

        result1 = evaluator.run_case(case)
        evaluator._results.clear()

        from sqlalchemy import text
        db.execute(text("TRUNCATE TABLE diagnostic_conversation_messages, diagnostic_results, diagnostic_sessions RESTART IDENTITY CASCADE"))
        db.commit()

        result2 = evaluator.run_case(case)

        assert result1.predicted_component == result2.predicted_component
        assert result1.predicted_system_category == result2.predicted_system_category
        assert result1.predicted_safety_tier == result2.predicted_safety_tier
        for m1, m2 in zip(result1.metrics, result2.metrics):
            assert m1.name == m2.name
            assert m1.result == m2.result
            assert m1.score == m2.score

    def test_top1_component_scoring_correct(self, evaluator_setup):
        evaluator, db, _ = evaluator_setup

        case = get_case("B001")
        result = evaluator.run_case(case)

        metric = result.get_metric("top1_component")
        assert metric is not None
        assert metric.result == EvaluationResult.PASS
        assert metric.score == 1.0
        assert metric.expected == "spark_plug"
        assert metric.actual == "spark_plug"

    def test_top3_component_scoring_correct(self, evaluator_setup):
        evaluator, db, _ = evaluator_setup

        case = get_case("B001")
        result = evaluator.run_case(case)

        metric = result.get_metric("top3_component")
        assert metric is not None
        assert metric.result == EvaluationResult.PASS
        assert metric.score == 1.0

    def test_top1_component_scoring_incorrect(self):
        db_engine = create_engine(settings.sqlalchemy_database_url, pool_pre_ping=True)
        from sqlalchemy.orm import sessionmaker
        SessionLocal = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
        db = SessionLocal()

        embedding_service = FakeEmbeddingService()

        case_responses = {
            "B001": {
                "status": "complete",
                "follow_up_question": None,
                "follow_up_reason": None,
                "fault_description": "Faulty alternator",
                "confidence_score": 0.8,
                "severity": "medium",
                "supporting_evidence": ["[dtc] P0300"],
                "recommended_checks": ["Test alternator"],
                "repair_suggestion": "Replace alternator",
                "expected_evidence_category": "dtc",
                "expected_entry_key": "P0300",
            },
        }
        llm_provider = CaseSpecificLLMProvider(case_responses)

        evaluator = DiagnosticEvaluator(
            db=db,
            embedding_service=embedding_service,
            llm_provider=llm_provider,
        )

        case = get_case("B001")
        result = evaluator.run_case(case)

        metric = result.get_metric("top1_component")
        assert metric is not None
        assert metric.result == EvaluationResult.FAIL
        assert metric.score == 0.0
        assert metric.expected == "spark_plug"
        assert metric.actual == "alternator"

        db.close()
        db_engine.dispose()


class TestDTCScoring:
    @pytest.fixture
    def dtc_evaluator(self):
        db_engine = create_engine(settings.sqlalchemy_database_url, pool_pre_ping=True)
        from sqlalchemy.orm import sessionmaker
        SessionLocal = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
        db = SessionLocal()

        embedding_service = FakeEmbeddingService()

        case_responses = {
            "B001": {
                "status": "complete",
                "follow_up_question": None,
                "follow_up_reason": None,
                "fault_description": "Faulty spark plug causing misfire",
                "confidence_score": 0.85,
                "severity": "high",
                "supporting_evidence": ["[dtc] P0300"],
                "recommended_checks": ["Inspect spark plugs"],
                "repair_suggestion": "Replace spark plugs",
                "expected_evidence_category": "dtc",
                "expected_entry_key": "P0300",
            },
        }
        llm_provider = CaseSpecificLLMProvider(case_responses)

        evaluator = DiagnosticEvaluator(
            db=db,
            embedding_service=embedding_service,
            llm_provider=llm_provider,
        )

        yield evaluator, db, db_engine

        db.close()
        db_engine.dispose()

    def test_dtc_match_scoring_pass(self, dtc_evaluator):
        evaluator, db, _ = dtc_evaluator

        case = get_case("B001")
        result = evaluator.run_case(case)

        metric = result.get_metric("dtc_match")
        assert metric is not None
        assert metric.result == EvaluationResult.PASS
        assert metric.score == 1.0

    def test_dtc_match_unavailable_for_no_dtc_cases(self):
        db_engine = create_engine(settings.sqlalchemy_database_url, pool_pre_ping=True)
        from sqlalchemy.orm import sessionmaker
        SessionLocal = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
        db = SessionLocal()

        embedding_service = FakeEmbeddingService()

        case_responses = {
            "B006": {
                "status": "needs_more_information",
                "follow_up_question": "Does the rough idle change?",
                "follow_up_reason": "Weak evidence",
                "fault_description": "Vacuum leak causing rough idle",
                "confidence_score": 0.65,
                "severity": "medium",
                "supporting_evidence": ["[symptom] rough_idle"],
                "recommended_checks": ["Smoke test"],
                "repair_suggestion": "Repair vacuum leak",
                "expected_evidence_category": "symptom",
                "expected_entry_key": "rough_idle",
            },
        }
        llm_provider = CaseSpecificLLMProvider(case_responses)

        evaluator = DiagnosticEvaluator(
            db=db,
            embedding_service=embedding_service,
            llm_provider=llm_provider,
        )

        case = get_case("B006")
        result = evaluator.run_case(case)

        metric = result.get_metric("dtc_match")
        assert metric is not None
        assert metric.result == EvaluationResult.UNAVAILABLE

        db.close()
        db_engine.dispose()


class TestSafetyTierScoring:
    @pytest.fixture
    def safety_evaluator(self):
        db_engine = create_engine(settings.sqlalchemy_database_url, pool_pre_ping=True)
        from sqlalchemy.orm import sessionmaker
        SessionLocal = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
        db = SessionLocal()

        embedding_service = FakeEmbeddingService()

        case_responses = {
            "B003": {
                "status": "complete",
                "follow_up_question": None,
                "follow_up_reason": None,
                "fault_description": "Restricted catalytic converter",
                "confidence_score": 0.8,
                "severity": "high",
                "supporting_evidence": ["[dtc] P0420"],
                "recommended_checks": ["Check exhaust"],
                "repair_suggestion": "Replace catalytic converter",
                "expected_evidence_category": "dtc",
                "expected_entry_key": "P0420",
            },
        }
        llm_provider = CaseSpecificLLMProvider(case_responses)

        evaluator = DiagnosticEvaluator(
            db=db,
            embedding_service=embedding_service,
            llm_provider=llm_provider,
        )

        yield evaluator, db, db_engine

        db.close()
        db_engine.dispose()

    def test_safety_tier_scoring_correct(self, safety_evaluator):
        evaluator, db, _ = safety_evaluator

        case = get_case("B003")
        result = evaluator.run_case(case)

        metric = result.get_metric("safety_tier")
        assert metric is not None
        assert metric.result == EvaluationResult.PASS
        assert metric.score == 1.0
        assert metric.expected == "immediate_professional"


class TestEvidenceScoring:
    @pytest.fixture
    def evidence_evaluator(self):
        db_engine = create_engine(settings.sqlalchemy_database_url, pool_pre_ping=True)
        from sqlalchemy.orm import sessionmaker
        SessionLocal = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
        db = SessionLocal()

        embedding_service = FakeEmbeddingService()

        case_responses = {
            "B001": {
                "status": "complete",
                "follow_up_question": None,
                "follow_up_reason": None,
                "fault_description": "Faulty spark plug causing misfire",
                "confidence_score": 0.85,
                "severity": "high",
                "supporting_evidence": ["[dtc] P0300"],
                "recommended_checks": ["Inspect spark plugs"],
                "repair_suggestion": "Replace spark plugs",
                "expected_evidence_category": "dtc",
                "expected_entry_key": "P0300",
            },
        }
        llm_provider = CaseSpecificLLMProvider(case_responses)

        evaluator = DiagnosticEvaluator(
            db=db,
            embedding_service=embedding_service,
            llm_provider=llm_provider,
        )

        yield evaluator, db, db_engine

        db.close()
        db_engine.dispose()

    def test_evidence_validity_scoring(self, evidence_evaluator):
        evaluator, db, _ = evidence_evaluator

        case = get_case("B001")
        result = evaluator.run_case(case)

        metric = result.get_metric("evidence_validity")
        assert metric is not None
        assert metric.result == EvaluationResult.PASS
        assert metric.score == 1.0


class TestFollowUpScoring:
    @pytest.fixture
    def followup_evaluator(self):
        db_engine = create_engine(settings.sqlalchemy_database_url, pool_pre_ping=True)
        from sqlalchemy.orm import sessionmaker
        SessionLocal = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
        db = SessionLocal()

        embedding_service = FakeEmbeddingService()

        case_responses = {
            "B006": {
                "status": "needs_more_information",
                "follow_up_question": "Does the rough idle change under load?",
                "follow_up_reason": "Weak evidence",
                "fault_description": "Vacuum leak causing rough idle",
                "confidence_score": 0.65,
                "severity": "medium",
                "supporting_evidence": ["[symptom] rough_idle"],
                "recommended_checks": ["Smoke test"],
                "repair_suggestion": "Repair vacuum leak",
                "expected_evidence_category": "symptom",
                "expected_entry_key": "rough_idle",
            },
        }
        llm_provider = CaseSpecificLLMProvider(case_responses)

        evaluator = DiagnosticEvaluator(
            db=db,
            embedding_service=embedding_service,
            llm_provider=llm_provider,
        )

        yield evaluator, db, db_engine

        db.close()
        db_engine.dispose()

    def test_follow_up_scoring_pass_when_expected(self, followup_evaluator):
        evaluator, db, _ = followup_evaluator

        case = get_case("B006")
        result = evaluator.run_case(case)

        metric = result.get_metric("follow_up_decision")
        assert metric is not None
        assert metric.result == EvaluationResult.PASS
        assert metric.score == 1.0

    def test_follow_up_scoring_fail_when_unexpected(self):
        db_engine = create_engine(settings.sqlalchemy_database_url, pool_pre_ping=True)
        from sqlalchemy.orm import sessionmaker
        SessionLocal = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
        db = SessionLocal()

        embedding_service = FakeEmbeddingService()

        case_responses = {
            "B001": {
                "status": "needs_more_information",
                "follow_up_question": "Does the misfire change under load?",
                "follow_up_reason": "Weak evidence",
                "fault_description": "Faulty spark plug causing misfire",
                "confidence_score": 0.85,
                "severity": "high",
                "supporting_evidence": ["[dtc] P0300"],
                "recommended_checks": ["Inspect spark plugs"],
                "repair_suggestion": "Replace spark plugs",
                "expected_evidence_category": "dtc",
                "expected_entry_key": "P0300",
            },
        }
        llm_provider = CaseSpecificLLMProvider(case_responses)

        evaluator = DiagnosticEvaluator(
            db=db,
            embedding_service=embedding_service,
            llm_provider=llm_provider,
        )

        case = get_case("B001")
        result = evaluator.run_case(case)

        metric = result.get_metric("follow_up_decision")
        assert metric is not None
        assert metric.result == EvaluationResult.FAIL
        assert metric.score == 0.0

        db.close()
        db_engine.dispose()


class TestAggregateMetrics:
    @pytest.fixture
    def full_evaluator(self):
        db_engine = create_engine(settings.sqlalchemy_database_url, pool_pre_ping=True)
        from sqlalchemy.orm import sessionmaker
        SessionLocal = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
        db = SessionLocal()

        embedding_service = FakeEmbeddingService()

        case_responses = {
            "B001": {
                "status": "complete",
                "follow_up_question": None,
                "follow_up_reason": None,
                "fault_description": "Faulty spark plug causing misfire",
                "confidence_score": 0.85,
                "severity": "high",
                "supporting_evidence": ["[dtc] P0300"],
                "recommended_checks": ["Inspect spark plugs"],
                "repair_suggestion": "Replace spark plugs",
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
                "recommended_checks": ["Clean MAF sensor"],
                "repair_suggestion": "Replace MAF sensor",
                "expected_evidence_category": "dtc",
                "expected_entry_key": "P0171",
            },
        }
        llm_provider = CaseSpecificLLMProvider(case_responses)

        evaluator = DiagnosticEvaluator(
            db=db,
            embedding_service=embedding_service,
            llm_provider=llm_provider,
        )

        yield evaluator, db, db_engine

        db.close()
        db_engine.dispose()

    def test_aggregate_metrics_totals(self, full_evaluator):
        evaluator, db, _ = full_evaluator

        case1 = get_case("B001")
        case2 = get_case("B002")

        evaluator.run_case(case1)
        evaluator.run_case(case2)

        aggregate = evaluator.compute_aggregate()

        assert aggregate.total_cases == 2
        assert aggregate.passed_cases == 2
        assert aggregate.failed_cases == 0

    def test_aggregate_accuracies(self, full_evaluator):
        evaluator, db, _ = full_evaluator

        case1 = get_case("B001")
        case2 = get_case("B002")

        evaluator.run_case(case1)
        evaluator.run_case(case2)

        aggregate = evaluator.compute_aggregate()

        assert aggregate.top1_component_accuracy == 1.0
        assert aggregate.top3_component_accuracy == 1.0
        assert aggregate.system_category_accuracy == 1.0
        assert aggregate.safety_tier_accuracy == 1.0
        assert aggregate.dtc_match_accuracy == 1.0
        assert aggregate.evidence_validity_rate == 1.0
        assert aggregate.follow_up_accuracy == 1.0

    def test_aggregate_metric_pass_rates(self, full_evaluator):
        evaluator, db, _ = full_evaluator

        case1 = get_case("B001")
        case2 = get_case("B002")

        evaluator.run_case(case1)
        evaluator.run_case(case2)

        aggregate = evaluator.compute_aggregate()

        assert "top1_component" in aggregate.metric_pass_rates
        assert "top3_component" in aggregate.metric_pass_rates
        assert "system_category" in aggregate.metric_pass_rates
        assert "safety_tier" in aggregate.metric_pass_rates
        assert "dtc_match" in aggregate.metric_pass_rates
        assert "evidence_validity" in aggregate.metric_pass_rates
        assert "follow_up_decision" in aggregate.metric_pass_rates


class TestDeterministicRepeatedRuns:
    def test_two_full_evaluation_runs_produce_identical_results(self):
        db_engine = create_engine(settings.sqlalchemy_database_url, pool_pre_ping=True)
        from sqlalchemy.orm import sessionmaker
        SessionLocal = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
        db1 = SessionLocal()

        from app.services.embeddings import get_embedding_service
        embedding_service1 = get_embedding_service()

        case_responses = {
            "B001": {
                "status": "complete",
                "follow_up_question": None,
                "follow_up_reason": None,
                "fault_description": "Faulty spark plug causing misfire",
                "confidence_score": 0.85,
                "severity": "high",
                "supporting_evidence": ["[dtc] P0300"],
                "recommended_checks": ["Inspect spark plugs"],
                "repair_suggestion": "Replace spark plugs",
                "expected_evidence_category": "dtc",
                "expected_entry_key": "P0300",
            },
        }
        llm_provider1 = CaseSpecificLLMProvider(case_responses)

        evaluator1 = DiagnosticEvaluator(
            db=db1,
            embedding_service=embedding_service1,
            llm_provider=llm_provider1,
        )

        case = get_case("B001")
        result1 = evaluator1.run_case(case)

        db1.execute(text("TRUNCATE TABLE diagnostic_conversation_messages, diagnostic_results, diagnostic_sessions RESTART IDENTITY CASCADE"))
        db1.commit()

        result2 = evaluator1.run_case(case)

        assert result1.predicted_component == result2.predicted_component
        assert result1.predicted_system_category == result2.predicted_system_category
        assert result1.predicted_safety_tier == result2.predicted_safety_tier
        for m1, m2 in zip(result1.metrics, result2.metrics):
            assert m1.result == m2.result
            assert m1.score == m2.score

        db1.close()
        db_engine.dispose()


class TestMockLLMInjection:
    def test_case_specific_llm_provider_used(self):
        db_engine = create_engine(settings.sqlalchemy_database_url, pool_pre_ping=True)
        from sqlalchemy.orm import sessionmaker
        SessionLocal = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
        db = SessionLocal()

        embedding_service = FakeEmbeddingService()

        case_responses = {
            "B001": {
                "status": "complete",
                "follow_up_question": None,
                "follow_up_reason": None,
                "fault_description": "Faulty spark plug causing misfire",
                "confidence_score": 0.85,
                "severity": "high",
                "supporting_evidence": ["[dtc] P0300"],
                "recommended_checks": ["Inspect spark plugs"],
                "repair_suggestion": "Replace spark plugs",
                "expected_evidence_category": "dtc",
                "expected_entry_key": "P0300",
            },
        }
        llm_provider = CaseSpecificLLMProvider(case_responses)

        evaluator = DiagnosticEvaluator(
            db=db,
            embedding_service=embedding_service,
            llm_provider=llm_provider,
        )

        case = get_case("B001")
        result = evaluator.run_case(case)

        assert isinstance(evaluator._llm_provider, CaseSpecificLLMProvider)
        assert result.predicted_component == "spark_plug"

        db.close()
        db_engine.dispose()

    def test_evaluation_llm_provider_works(self):
        db_engine = create_engine(settings.sqlalchemy_database_url, pool_pre_ping=True)
        from sqlalchemy.orm import sessionmaker
        SessionLocal = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
        db = SessionLocal()

        embedding_service = FakeEmbeddingService()

        responses = {
            "default": '{"status": "complete", "hypotheses": [{"fault_description": "Faulty spark plug", "confidence_score": 0.8, "severity": "high", "supporting_evidence": [], "recommended_checks": [], "repair_suggestion": null, "evidence_references": [], "differential_rank": 1}]}'
        }
        llm_provider = EvaluationLLMProvider(responses)

        evaluator = DiagnosticEvaluator(
            db=db,
            embedding_service=embedding_service,
            llm_provider=llm_provider,
        )

        case = get_case("B001")
        result = evaluator.run_case(case)

        assert isinstance(evaluator._llm_provider, EvaluationLLMProvider)

        db.close()
        db_engine.dispose()


class TestEvaluationWithoutOllama:
    def test_evaluation_uses_mock_llm_not_ollama(self):
        from evaluation.mock_llm import CaseSpecificLLMProvider
        from evaluation.runner import DiagnosticEvaluator

        db_engine = create_engine(settings.sqlalchemy_database_url, pool_pre_ping=True)
        from sqlalchemy.orm import sessionmaker
        SessionLocal = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
        db = SessionLocal()

        embedding_service = FakeEmbeddingService()

        case_responses = {
            "B001": {
                "status": "complete",
                "follow_up_question": None,
                "follow_up_reason": None,
                "fault_description": "Faulty spark plug causing misfire",
                "confidence_score": 0.85,
                "severity": "high",
                "supporting_evidence": ["[dtc] P0300"],
                "recommended_checks": ["Inspect spark plugs"],
                "repair_suggestion": "Replace spark plugs",
                "expected_evidence_category": "dtc",
                "expected_entry_key": "P0300",
            },
        }
        llm_provider = CaseSpecificLLMProvider(case_responses)

        evaluator = DiagnosticEvaluator(
            db=db,
            embedding_service=embedding_service,
            llm_provider=llm_provider,
        )

        case = get_case("B001")
        result = evaluator.run_case(case)

        assert not isinstance(llm_provider, type(None))
        assert result.predicted_component == "spark_plug"
        assert result.error is None

        db.close()
        db_engine.dispose()


