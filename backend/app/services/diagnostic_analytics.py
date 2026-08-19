from pydantic import BaseModel

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import models


class DiagnosticAnalytics(BaseModel):
    total_sessions: int
    total_results: int
    results_by_status: dict[str, int]
    checks_by_status: dict[str, int]
    top_dtcs: list[tuple[str, int]]
    top_confirmed_faults: list[tuple[str, int]]


class DiagnosticAnalyticsService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_outcome_analytics(self) -> DiagnosticAnalytics:
        total_sessions = self._db.query(func.count(models.DiagnosticSession.id)).scalar() or 0
        total_results = self._db.query(func.count(models.DiagnosticResult.id)).scalar() or 0

        status_rows = (
            self._db.query(models.DiagnosticResult.hypothesis_status, func.count(models.DiagnosticResult.id))
            .group_by(models.DiagnosticResult.hypothesis_status)
            .all()
        )
        results_by_status = {row[0]: row[1] for row in status_rows}

        check_status_rows = (
            self._db.query(models.DiagnosticCheckOutcome.status, func.count(models.DiagnosticCheckOutcome.id))
            .group_by(models.DiagnosticCheckOutcome.status)
            .all()
        )
        checks_by_status = {row[0]: row[1] for row in check_status_rows}

        dtc_rows = (
            self._db.query(models.DiagnosticSession.dtc_codes)
            .filter(models.DiagnosticSession.dtc_codes.is_not(None))
            .all()
        )
        dtc_counter: dict[str, int] = {}
        for row in dtc_rows:
            for code in (row[0] or "").split(","):
                code = code.strip().upper()
                if code:
                    dtc_counter[code] = dtc_counter.get(code, 0) + 1
        top_dtcs = sorted(dtc_counter.items(), key=lambda x: x[1], reverse=True)[:10]

        confirmed_rows = (
            self._db.query(models.DiagnosticResult.fault_description)
            .filter(models.DiagnosticResult.hypothesis_status == "confirmed")
            .all()
        )
        fault_counter: dict[str, int] = {}
        for row in confirmed_rows:
            desc = (row[0] or "").strip()
            if desc:
                fault_counter[desc] = fault_counter.get(desc, 0) + 1
        top_confirmed_faults = sorted(fault_counter.items(), key=lambda x: x[1], reverse=True)[:10]

        return DiagnosticAnalytics(
            total_sessions=total_sessions,
            total_results=total_results,
            results_by_status=results_by_status,
            checks_by_status=checks_by_status,
            top_dtcs=top_dtcs,
            top_confirmed_faults=top_confirmed_faults,
        )


def get_diagnostic_analytics_service(db: Session) -> DiagnosticAnalyticsService:
    return DiagnosticAnalyticsService(db)
