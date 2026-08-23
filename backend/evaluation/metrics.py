"""
Evaluation metrics and result types.

Provides structured types for evaluation results and metrics.
"""
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class EvaluationResult(Enum):
    """Result of a single metric evaluation."""
    PASS = "pass"
    FAIL = "fail"
    UNAVAILABLE = "unavailable"


@dataclass
class MetricResult:
    """Result of a single metric check."""
    name: str
    result: EvaluationResult
    expected: Optional[str] = None
    actual: Optional[str] = None
    details: str = ""
    score: float = 0.0  # 1.0 for pass, 0.0 for fail, 0.5 for partial


@dataclass
class CaseEvaluationResult:
    """Complete evaluation result for a single benchmark case."""
    case_id: str
    description: str
    metrics: list[MetricResult] = field(default_factory=list)
    predicted_component: Optional[str] = None
    predicted_system_category: Optional[str] = None
    predicted_safety_tier: Optional[str] = None
    predicted_status: Optional[str] = None
    follow_up_question: Optional[str] = None
    evidence_references_count: int = 0
    valid_evidence_references: int = 0
    top_components: list[str] = field(default_factory=list)
    error: Optional[str] = None

    def get_metric(self, name: str) -> Optional[MetricResult]:
        """Get a specific metric by name."""
        for m in self.metrics:
            if m.name == name:
                return m
        return None

    def passed_count(self) -> int:
        return sum(1 for m in self.metrics if m.result == EvaluationResult.PASS)

    def failed_count(self) -> int:
        return sum(1 for m in self.metrics if m.result == EvaluationResult.FAIL)

    def unavailable_count(self) -> int:
        return sum(1 for m in self.metrics if m.result == EvaluationResult.UNAVAILABLE)

    def total_score(self) -> float:
        return sum(m.score for m in self.metrics)

    def max_possible_score(self) -> float:
        return sum(1.0 for m in self.metrics if m.result != EvaluationResult.UNAVAILABLE)


@dataclass
class AggregateMetrics:
    """Aggregate evaluation metrics across all cases."""
    total_cases: int = 0
    passed_cases: int = 0  # Cases where all available metrics pass
    failed_cases: int = 0
    top1_component_accuracy: float = 0.0
    top3_component_accuracy: float = 0.0
    system_category_accuracy: float = 0.0
    safety_tier_accuracy: float = 0.0
    follow_up_accuracy: float = 0.0
    evidence_validity_rate: float = 0.0
    dtc_match_accuracy: float = 0.0
    avg_score_per_case: float = 0.0

    # Per-metric breakdown
    metric_pass_rates: dict[str, float] = field(default_factory=dict)


class FailureCategory(Enum):
    """Category of evaluation failure for breakdown analysis."""
    RETRIEVAL = "retrieval"
    LLM_REASONING = "llm_reasoning"
    BACKEND_VALIDATION = "backend_validation"
    SAFETY_RULE = "safety_rule"
    UNKNOWN = "unknown"