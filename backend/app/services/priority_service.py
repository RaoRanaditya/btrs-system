"""
services/priority_service.py
-----------------------------
Thin wrapper — delegates to RuleEngine (core/rules.py).
Paper section 6.3: priority scoring.
Kept for backwards compatibility.
"""
from app.core.rules import RuleEngine, PriorityResult


class PriorityService:
    @staticmethod
    def compute_priority(
        severity: int | str,
        impact: int,
        frequency: int,
        reproducibility: int,
    ) -> PriorityResult:
        return RuleEngine.compute_priority(
            severity=severity,
            impact=impact,
            frequency=frequency,
            reproducibility=reproducibility,
        )