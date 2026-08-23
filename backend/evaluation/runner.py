"""
Main evaluation runner.

Orchestrates running benchmark cases through the diagnostic pipeline
and collecting evaluation metrics.
"""
import json
import uuid
from typing import Optional
from sqlalchemy.orm import Session

from app.config import Settings, settings
from app.db.database import engine
from app.services.diagnostic import DiagnosticService
from app.services.embeddings import EmbeddingService, get_embedding_service
from app.services.llm import LLMProvider
from app.schemas import DiagnosticAnalyzeRequest, DiagnosticHypothesis, EvidenceReference
from tests.benchmark_cases import BenchmarkCase, get_all_cases
from tests.conftest import FakeEmbeddingService

from .mock_llm import CaseSpecificLLMProvider
from .metrics import (
    CaseEvaluationResult,
    AggregateMetrics,
    MetricResult,
    EvaluationResult,
    FailureCategory,
)


class DiagnosticEvaluator:
    """Evaluates the diagnostic pipeline against benchmark cases."""

    def __init__(
        self,
        db: Session,
        embedding_service: EmbeddingService,
        llm_provider: LLMProvider,
        app_settings: Settings = settings,
    ) -> None:
        self._db = db
        self._embedding_service = embedding_service
        self._llm_provider = llm_provider
        self._settings = app_settings
        self._service = DiagnosticService(
            app_settings=app_settings,
            embedding_service=embedding_service,
            llm_service=llm_provider,  # type: ignore
        )
        self._results: list[CaseEvaluationResult] = []

    def run_case(self, case: BenchmarkCase) -> CaseEvaluationResult:
        """Run a single benchmark case through the diagnostic pipeline."""
        result = CaseEvaluationResult(
            case_id=case.case_id,
            description=case.description,
        )

        try:
            # Set up case-specific LLM response if provider supports it
            if isinstance(self._llm_provider, CaseSpecificLLMProvider):
                self._llm_provider.set_current_case(case.case_id)

            # Create request from benchmark case
            request = case.to_request()

            # Run diagnostic analysis
            response = self._service.analyze(self._db, request)

            # Extract predictions
            if response.hypotheses:
                top_hypothesis = response.hypotheses[0]
                result.predicted_component = top_hypothesis.component_id
                result.predicted_system_category = top_hypothesis.system_category
                result.predicted_safety_tier = top_hypothesis.safety_tier
                result.predicted_status = response.status
                result.follow_up_question = response.follow_up_question
                result.evidence_references_count = len(top_hypothesis.evidence_references)
                result.valid_evidence_references = sum(
                    1 for ref in top_hypothesis.evidence_references
                    if ref.evidence_id is not None
                )
                result.top_components = [h.component_id for h in response.hypotheses if h.component_id]
            else:
                result.error = "No hypotheses generated"

            # Evaluate metrics
            self._evaluate_case(case, response, result)

        except Exception as e:
            result.error = f"Exception during evaluation: {str(e)}"
            result.metrics.append(MetricResult(
                name="execution",
                result=EvaluationResult.FAIL,
                details=str(e),
                score=0.0,
            ))

        self._results.append(result)
        return result

    def _evaluate_case(
        self,
        case: BenchmarkCase,
        response: "DiagnosticAnalyzeResponse",
        result: CaseEvaluationResult,
    ) -> None:
        """Evaluate all metrics for a single case."""

        # 1. Top-1 Component Accuracy
        self._evaluate_top1_component(case, response, result)

        # 2. Top-3 Component Accuracy
        self._evaluate_top3_component(case, response, result)

        # 3. System Category Accuracy
        self._evaluate_system_category(case, response, result)

        # 4. Safety Tier Accuracy
        self._evaluate_safety_tier(case, response, result)

        # 5. DTC Match Accuracy (if DTC codes provided)
        self._evaluate_dtc_match(case, response, result)

        # 6. Evidence Reference Validity
        self._evaluate_evidence_validity(case, response, result)

        # 7. Follow-up Decision Accuracy
        self._evaluate_follow_up(case, response, result)

    def _evaluate_top1_component(
        self,
        case: BenchmarkCase,
        response: "DiagnosticAnalyzeResponse",
        eval_result: CaseEvaluationResult,
    ) -> None:
        """Evaluate top-1 component accuracy."""
        if not response.hypotheses:
            eval_result.metrics.append(MetricResult(
                name="top1_component",
                result=EvaluationResult.FAIL,
                expected=case.expected_component_id,
                actual="none",
                details="No hypotheses generated",
                score=0.0,
            ))
            return

        predicted = response.hypotheses[0].component_id
        expected = case.expected_component_id
        alternatives = case.acceptable_alternative_components

        is_correct = False
        if predicted == expected:
            is_correct = True
        elif predicted in alternatives:
            is_correct = True

        eval_result.metrics.append(MetricResult(
            name="top1_component",
            result=EvaluationResult.PASS if is_correct else EvaluationResult.FAIL,
            expected=expected,
            actual=predicted,
            details=f"Top hypothesis component: {predicted or 'none'}",
            score=1.0 if is_correct else 0.0,
        ))

    def _evaluate_top3_component(
        self,
        case: BenchmarkCase,
        response: "DiagnosticAnalyzeResponse",
        eval_result: CaseEvaluationResult,
    ) -> None:
        """Evaluate top-3 component accuracy."""
        if not response.hypotheses:
            eval_result.metrics.append(MetricResult(
                name="top3_component",
                result=EvaluationResult.FAIL,
                expected=case.expected_component_id,
                actual="none",
                details="No hypotheses generated",
                score=0.0,
            ))
            return

        top_components = [h.component_id for h in response.hypotheses[:3] if h.component_id]
        expected = case.expected_component_id
        alternatives = case.acceptable_alternative_components
        all_acceptable = [expected] + alternatives

        is_correct = any(comp in all_acceptable for comp in top_components)

        eval_result.metrics.append(MetricResult(
            name="top3_component",
            result=EvaluationResult.PASS if is_correct else EvaluationResult.FAIL,
            expected=expected,
            actual=", ".join(top_components),
            details=f"Top 3 components: {', '.join(top_components) or 'none'}",
            score=1.0 if is_correct else 0.0,
        ))

    def _evaluate_system_category(
        self,
        case: BenchmarkCase,
        response: "DiagnosticAnalyzeResponse",
        eval_result: CaseEvaluationResult,
    ) -> None:
        """Evaluate system category accuracy."""
        if not response.hypotheses or not case.expected_system_category:
            eval_result.metrics.append(MetricResult(
                name="system_category",
                result=EvaluationResult.UNAVAILABLE,
                expected=case.expected_system_category,
                actual=response.hypotheses[0].system_category if response.hypotheses else "none",
                details="No expected system category defined or no hypotheses",
                score=0.0,
            ))
            return

        predicted = response.hypotheses[0].system_category
        expected = case.expected_system_category

        is_correct = predicted == expected

        eval_result.metrics.append(MetricResult(
            name="system_category",
            result=EvaluationResult.PASS if is_correct else EvaluationResult.FAIL,
            expected=expected,
            actual=predicted,
            details=f"Predicted system category: {predicted or 'none'}",
            score=1.0 if is_correct else 0.0,
        ))

    def _evaluate_safety_tier(
        self,
        case: BenchmarkCase,
        response: "DiagnosticAnalyzeResponse",
        eval_result: CaseEvaluationResult,
    ) -> None:
        """Evaluate safety tier accuracy."""
        if not response.hypotheses or not case.expected_safety_tier:
            eval_result.metrics.append(MetricResult(
                name="safety_tier",
                result=EvaluationResult.UNAVAILABLE,
                expected=case.expected_safety_tier,
                actual=response.hypotheses[0].safety_tier if response.hypotheses else "none",
                details="No expected safety tier defined or no hypotheses",
                score=0.0,
            ))
            return

        predicted = response.hypotheses[0].safety_tier
        expected = case.expected_safety_tier

        is_correct = predicted == expected

        eval_result.metrics.append(MetricResult(
            name="safety_tier",
            result=EvaluationResult.PASS if is_correct else EvaluationResult.FAIL,
            expected=expected,
            actual=predicted,
            details=f"Predicted safety tier: {predicted or 'none'}",
            score=1.0 if is_correct else 0.0,
        ))

    def _evaluate_dtc_match(
        self,
        case: BenchmarkCase,
        response: "DiagnosticAnalyzeResponse",
        eval_result: CaseEvaluationResult,
    ) -> None:
        """Evaluate DTC matching accuracy."""
        if not case.dtc_codes:
            eval_result.metrics.append(MetricResult(
                name="dtc_match",
                result=EvaluationResult.UNAVAILABLE,
                expected="N/A",
                actual="N/A",
                details="No DTC codes in benchmark case",
                score=0.0,
            ))
            return

        # Check if any retrieved evidence contains the expected DTC codes
        expected_dtcs = set(case.dtc_codes)
        found_dtcs = set()

        for evidence in response.evidence:
            if evidence.category == "dtc" and evidence.entry_key:
                if evidence.entry_key.upper() in expected_dtcs:
                    found_dtcs.add(evidence.entry_key.upper())

        # Check if the top hypothesis references DTC evidence
        dtc_referenced = False
        if response.hypotheses:
            for ref in response.hypotheses[0].evidence_references:
                if ref.category == "dtc" and ref.entry_key:
                    if ref.entry_key.upper() in expected_dtcs:
                        dtc_referenced = True

        all_found = expected_dtcs.issubset(found_dtcs)

        eval_result.metrics.append(MetricResult(
            name="dtc_match",
            result=EvaluationResult.PASS if all_found else EvaluationResult.FAIL,
            expected=", ".join(expected_dtcs),
            actual=", ".join(found_dtcs) if found_dtcs else "none",
            details=f"DTC evidence found: {', '.join(found_dtcs) or 'none'}; DTC referenced in hypothesis: {dtc_referenced}",
            score=1.0 if all_found else 0.0,
        ))

    def _evaluate_evidence_validity(
        self,
        case: BenchmarkCase,
        response: "DiagnosticAnalyzeResponse",
        eval_result: CaseEvaluationResult,
    ) -> None:
        """Evaluate evidence reference validity."""
        if not response.hypotheses:
            eval_result.metrics.append(MetricResult(
                name="evidence_validity",
                result=EvaluationResult.FAIL,
                expected=">0",
                actual="0",
                details="No hypotheses to evaluate evidence",
                score=0.0,
            ))
            return

        total_refs = 0
        valid_refs = 0

        for hypothesis in response.hypotheses:
            total_refs += len(hypothesis.evidence_references)
            for ref in hypothesis.evidence_references:
                # Check if evidence_id matches any retrieved evidence
                if any(ref.evidence_id == e.id for e in response.evidence):
                    valid_refs += 1

        validity_rate = valid_refs / total_refs if total_refs > 0 else 1.0

        eval_result.metrics.append(MetricResult(
            name="evidence_validity",
            result=EvaluationResult.PASS if validity_rate >= 0.8 else EvaluationResult.FAIL,
            expected="all valid",
            actual=f"{valid_refs}/{total_refs} valid",
            details=f"Evidence validity rate: {validity_rate:.2f}",
            score=validity_rate,
        ))

    def _evaluate_follow_up(
        self,
        case: BenchmarkCase,
        response: "DiagnosticAnalyzeResponse",
        eval_result: CaseEvaluationResult,
    ) -> None:
        """Evaluate follow-up decision accuracy."""
        expected_follow_up = case.expects_follow_up
        actual_follow_up = response.status == "needs_more_information"

        # If expected follow-up, check if the question contains relevant keywords
        keyword_match = True
        if expected_follow_up and actual_follow_up and case.follow_up_reason_keywords:
            question = (response.follow_up_question or "").lower()
            keyword_match = any(kw.lower() in question for kw in case.follow_up_reason_keywords)

        is_correct = (expected_follow_up == actual_follow_up) and keyword_match

        eval_result.metrics.append(MetricResult(
            name="follow_up_decision",
            result=EvaluationResult.PASS if is_correct else EvaluationResult.FAIL,
            expected="follow_up" if expected_follow_up else "complete",
            actual="follow_up" if actual_follow_up else "complete",
            details=f"Expected follow-up: {expected_follow_up}, got: {actual_follow_up}; Question: {response.follow_up_question or 'N/A'}",
            score=1.0 if is_correct else 0.0,
        ))

    def run_all_cases(self) -> list[CaseEvaluationResult]:
        """Run all benchmark cases."""
        cases = get_all_cases()
        for case in cases:
            # Clean up conversation messages table between cases to avoid cross-contamination
            from sqlalchemy import text
            self._db.execute(text("TRUNCATE TABLE diagnostic_conversation_messages, diagnostic_results, diagnostic_sessions RESTART IDENTITY CASCADE"))
            self._db.commit()

            self.run_case(case)
        return self._results

    def compute_aggregate(self) -> AggregateMetrics:
        """Compute aggregate metrics from all case results."""
        if not self._results:
            return AggregateMetrics()

        agg = AggregateMetrics()
        agg.total_cases = len(self._results)

        # Count passed/failed cases (a case passes if all its non-unavailable metrics pass)
        for result in self._results:
            non_unavail = [m for m in result.metrics if m.result != EvaluationResult.UNAVAILABLE]
            if non_unavail and all(m.result == EvaluationResult.PASS for m in non_unavail):
                agg.passed_cases += 1
            else:
                agg.failed_cases += 1

        # Top-1 component accuracy
        top1_passes = sum(1 for r in self._results
                         if r.get_metric("top1_component") and r.get_metric("top1_component").result == EvaluationResult.PASS)
        agg.top1_component_accuracy = top1_passes / agg.total_cases if agg.total_cases > 0 else 0.0

        # Top-3 component accuracy
        top3_passes = sum(1 for r in self._results
                         if r.get_metric("top3_component") and r.get_metric("top3_component").result == EvaluationResult.PASS)
        agg.top3_component_accuracy = top3_passes / agg.total_cases if agg.total_cases > 0 else 0.0

        # System category accuracy
        sys_passes = sum(1 for r in self._results
                        if r.get_metric("system_category") and r.get_metric("system_category").result == EvaluationResult.PASS)
        sys_total = sum(1 for r in self._results
                       if r.get_metric("system_category") and r.get_metric("system_category").result != EvaluationResult.UNAVAILABLE)
        agg.system_category_accuracy = sys_passes / sys_total if sys_total > 0 else 0.0

        # Safety tier accuracy
        safety_passes = sum(1 for r in self._results
                           if r.get_metric("safety_tier") and r.get_metric("safety_tier").result == EvaluationResult.PASS)
        safety_total = sum(1 for r in self._results
                          if r.get_metric("safety_tier") and r.get_metric("safety_tier").result != EvaluationResult.UNAVAILABLE)
        agg.safety_tier_accuracy = safety_passes / safety_total if safety_total > 0 else 0.0

        # Follow-up accuracy
        followup_passes = sum(1 for r in self._results
                             if r.get_metric("follow_up_decision") and r.get_metric("follow_up_decision").result == EvaluationResult.PASS)
        followup_total = sum(1 for r in self._results
                            if r.get_metric("follow_up_decision") and r.get_metric("follow_up_decision").result != EvaluationResult.UNAVAILABLE)
        agg.follow_up_accuracy = followup_passes / followup_total if followup_total > 0 else 0.0

        # Evidence validity rate
        evidence_rates = [r.get_metric("evidence_validity").score
                         for r in self._results if r.get_metric("evidence_validity")]
        agg.evidence_validity_rate = sum(evidence_rates) / len(evidence_rates) if evidence_rates else 0.0

        # DTC match accuracy
        dtc_passes = sum(1 for r in self._results
                        if r.get_metric("dtc_match") and r.get_metric("dtc_match").result == EvaluationResult.PASS)
        dtc_total = sum(1 for r in self._results
                       if r.get_metric("dtc_match") and r.get_metric("dtc_match").result != EvaluationResult.UNAVAILABLE)
        agg.dtc_match_accuracy = dtc_passes / dtc_total if dtc_total > 0 else 0.0

        # Average score per case
        case_scores = [r.total_score() / r.max_possible_score() if r.max_possible_score() > 0 else 0.0
                      for r in self._results]
        agg.avg_score_per_case = sum(case_scores) / len(case_scores) if case_scores else 0.0

        # Per-metric pass rates
        metric_names = [
            "top1_component", "top3_component", "system_category",
            "safety_tier", "dtc_match", "evidence_validity", "follow_up_decision"
        ]
        for name in metric_names:
            passes = sum(1 for r in self._results
                        if r.get_metric(name) and r.get_metric(name).result == EvaluationResult.PASS)
            total = sum(1 for r in self._results
                       if r.get_metric(name) and r.get_metric(name).result != EvaluationResult.UNAVAILABLE)
            agg.metric_pass_rates[name] = passes / total if total > 0 else 0.0

        return agg