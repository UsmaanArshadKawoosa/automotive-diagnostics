"""
Evaluation report generator.

Generates human-readable and machine-readable evaluation reports.
"""
import json
from datetime import datetime
from typing import TextIO

from .metrics import CaseEvaluationResult, AggregateMetrics, MetricResult, EvaluationResult
from .runner import DiagnosticEvaluator


class EvaluationReporter:
    """Generates evaluation reports."""

    def __init__(self, evaluator: DiagnosticEvaluator, aggregate: AggregateMetrics) -> None:
        self._evaluator = evaluator
        self._aggregate = aggregate

    def generate_json(self) -> dict:
        """Generate a machine-readable JSON report."""
        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "summary": {
                "total_cases": self._aggregate.total_cases,
                "passed_cases": self._aggregate.passed_cases,
                "failed_cases": self._aggregate.failed_cases,
                "top1_component_accuracy": round(self._aggregate.top1_component_accuracy, 4),
                "top3_component_accuracy": round(self._aggregate.top3_component_accuracy, 4),
                "system_category_accuracy": round(self._aggregate.system_category_accuracy, 4),
                "safety_tier_accuracy": round(self._aggregate.safety_tier_accuracy, 4),
                "follow_up_accuracy": round(self._aggregate.follow_up_accuracy, 4),
                "evidence_validity_rate": round(self._aggregate.evidence_validity_rate, 4),
                "dtc_match_accuracy": round(self._aggregate.dtc_match_accuracy, 4),
                "avg_score_per_case": round(self._aggregate.avg_score_per_case, 4),
            },
            "metric_pass_rates": {
                k: round(v, 4) for k, v in self._aggregate.metric_pass_rates.items()
            },
            "cases": [
                self._case_to_dict(case) for case in self._evaluator._results
            ],
        }

    def _case_to_dict(self, case: CaseEvaluationResult) -> dict:
        return {
            "case_id": case.case_id,
            "description": case.description,
            "predictions": {
                "component": case.predicted_component,
                "system_category": case.predicted_system_category,
                "safety_tier": case.predicted_safety_tier,
                "status": case.predicted_status,
                "top_components": case.top_components,
            },
            "metrics": [
                {
                    "name": m.name,
                    "result": m.result.value,
                    "expected": m.expected,
                    "actual": m.actual,
                    "score": m.score,
                    "details": m.details,
                }
                for m in case.metrics
            ],
            "error": case.error,
        }

    def generate_human_readable(self, output: TextIO) -> None:
        """Generate a human-readable report."""
        agg = self._aggregate

        output.write("=" * 80 + "\n")
        output.write("DIAGNOSTIC EVALUATION REPORT\n")
        output.write("=" * 80 + "\n\n")

        output.write(f"Timestamp: {datetime.utcnow().isoformat()}Z\n")
        output.write(f"Total Benchmark Cases: {agg.total_cases}\n")
        output.write(f"Passed Cases: {agg.passed_cases}\n")
        output.write(f"Failed Cases: {agg.failed_cases}\n\n")

        output.write("-" * 80 + "\n")
        output.write("AGGREGATE METRICS\n")
        output.write("-" * 80 + "\n\n")

        output.write(f"Top-1 Component Accuracy:     {agg.top1_component_accuracy:.2%}\n")
        output.write(f"Top-3 Component Accuracy:     {agg.top3_component_accuracy:.2%}\n")
        output.write(f"System Category Accuracy:     {agg.system_category_accuracy:.2%}\n")
        output.write(f"Safety Tier Accuracy:         {agg.safety_tier_accuracy:.2%}\n")
        output.write(f"Follow-up Decision Accuracy:  {agg.follow_up_accuracy:.2%}\n")
        output.write(f"Evidence Validity Rate:       {agg.evidence_validity_rate:.2%}\n")
        output.write(f"DTC Match Accuracy:           {agg.dtc_match_accuracy:.2%}\n")
        output.write(f"Avg Score Per Case:           {agg.avg_score_per_case:.2%}\n\n")

        output.write("-" * 80 + "\n")
        output.write("PER-METRIC PASS RATES\n")
        output.write("-" * 80 + "\n\n")

        for name, rate in agg.metric_pass_rates.items():
            output.write(f"  {name}: {rate:.2%}\n")

        output.write("\n" + "=" * 80 + "\n")
        output.write("PER-CASE RESULTS\n")
        output.write("=" * 80 + "\n\n")

        for case in self._evaluator._results:
            output.write(f"Case {case.case_id}: {case.description}\n")
            output.write("-" * 40 + "\n")

            if case.error:
                output.write(f"  ERROR: {case.error}\n\n")
                continue

            output.write(f"  Predicted Component:    {case.predicted_component or 'N/A'}\n")
            output.write(f"  Predicted System:       {case.predicted_system_category or 'N/A'}\n")
            output.write(f"  Predicted Safety Tier:  {case.predicted_safety_tier or 'N/A'}\n")
            output.write(f"  Status:                 {case.predicted_status or 'N/A'}\n")
            output.write(f"  Top Components:         {', '.join(case.top_components) or 'N/A'}\n")
            output.write(f"  Evidence Refs:          {case.valid_evidence_references}/{case.evidence_references_count} valid\n")

            for metric in case.metrics:
                status_symbol = {
                    EvaluationResult.PASS: "✓",
                    EvaluationResult.FAIL: "✗",
                    EvaluationResult.UNAVAILABLE: "~",
                }.get(metric.result, "?")
                output.write(f"  {status_symbol} {metric.name}: {metric.result.value}")
                if metric.expected is not None:
                    output.write(f" (expected: {metric.expected}, actual: {metric.actual})")
                output.write(f" - score: {metric.score:.2f}\n")

            output.write("\n")

    def save_json(self, filepath: str) -> None:
        """Save JSON report to file."""
        with open(filepath, "w") as f:
            json.dump(self.generate_json(), f, indent=2)

    def save_human_readable(self, filepath: str) -> None:
        """Save human-readable report to file."""
        with open(filepath, "w") as f:
            self.generate_human_readable(f)


def print_failure_breakdown(evaluator: DiagnosticEvaluator) -> None:
    """Print a breakdown of failure categories."""
    print("\n" + "=" * 80)
    print("FAILURE BREAKDOWN")
    print("=" * 80)

    # Group failures by metric
    failures_by_metric = {}
    for case in evaluator._results:
        for metric in case.metrics:
            if metric.result == EvaluationResult.FAIL:
                if metric.name not in failures_by_metric:
                    failures_by_metric[metric.name] = []
                failures_by_metric[metric.name].append({
                    "case_id": case.case_id,
                    "expected": metric.expected,
                    "actual": metric.actual,
                    "details": metric.details,
                })

    if not failures_by_metric:
        print("No failures!")
        return

    for metric_name, failures in failures_by_metric.items():
        print(f"\n{metric_name} ({len(failures)} failures):")
        for f in failures[:5]:  # Show first 5
            print(f"  Case {f['case_id']}: expected={f['expected']}, actual={f['actual']}")
            if f['details']:
                print(f"    {f['details']}")
        if len(failures) > 5:
            print(f"  ... and {len(failures) - 5} more")