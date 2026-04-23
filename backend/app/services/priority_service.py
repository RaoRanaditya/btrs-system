"""
Priority Service
Weighted scoring formula — fully rule-based, deterministic.

Factors
-------
| Factor          | Weight | Valid input values (1–5) |
|-----------------|--------|--------------------------|
| severity        |  0.40  | 1 = negligible … 5 = critical |
| impact          |  0.30  | 1 = minimal    … 5 = system-wide |
| frequency       |  0.20  | 1 = rare       … 5 = always |
| reproducibility |  0.10  | 1 = not repro  … 5 = always repro |

Score range : 1.0 – 5.0
Thresholds  : High ≥ 3.5 | Medium ≥ 2.0 | Low < 2.0
"""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration — change weights here without touching business logic
# ---------------------------------------------------------------------------
WEIGHTS: dict[str, float] = {
    "severity":        0.40,
    "impact":          0.30,
    "frequency":       0.20,
    "reproducibility": 0.10,
}

THRESHOLDS: dict[str, float] = {
    "High":   3.5,
    "Medium": 2.0,
    # Low is the fallback (score < 2.0)
}

VALID_RANGE = range(1, 6)  # 1 – 5 inclusive


@dataclass(frozen=True)
class PriorityResult:
    priority: str        # "High" | "Medium" | "Low"
    score: float         # raw weighted score (rounded to 2 dp)
    breakdown: dict      # per-factor weighted contributions


class PriorityService:
    """
    Computes bug priority from four numeric factors using a weighted formula.
    """

    @staticmethod
    def _validate(name: str, value: int) -> None:
        if not isinstance(value, int) or value not in VALID_RANGE:
            raise ValueError(
                f"Factor '{name}' must be an integer between 1 and 5, got: {value}"
            )

    @staticmethod
    def compute_priority(
        severity: int,
        impact: int,
        frequency: int,
        reproducibility: int,
    ) -> PriorityResult:
        """
        Compute a bug's priority level.

        Args:
            severity        : How severe is the bug? (1–5)
            impact          : How many users / systems are affected? (1–5)
            frequency       : How often does it occur? (1–5)
            reproducibility : How reliably can it be reproduced? (1–5)

        Returns:
            PriorityResult with .priority, .score, and .breakdown
        """
        # --- Input validation ---
        factors = {
            "severity":        severity,
            "impact":          impact,
            "frequency":       frequency,
            "reproducibility": reproducibility,
        }

        for name, value in factors.items():
            PriorityService._validate(name, value)

        # --- Weighted score calculation ---
        breakdown: dict[str, float] = {}
        total_score: float = 0.0

        for name, value in factors.items():
            weight = WEIGHTS[name]
            contribution = round(value * weight, 4)
            breakdown[name] = contribution
            total_score += contribution

        total_score = round(total_score, 2)

        # --- Priority band assignment ---
        if total_score >= THRESHOLDS["High"]:
            priority = "High"
        elif total_score >= THRESHOLDS["Medium"]:
            priority = "Medium"
        else:
            priority = "Low"

        logger.debug(
            "Priority computed: score=%.2f → %s | breakdown=%s",
            total_score,
            priority,
            breakdown,
        )

        return PriorityResult(
            priority=priority,
            score=total_score,
            breakdown=breakdown,
        )

    @staticmethod
    def get_priority_label(score: float) -> str:
        """
        Derive a priority label directly from a pre-computed score.
        Useful when the score is already stored in the DB.
        """
        if score >= THRESHOLDS["High"]:
            return "High"
        elif score >= THRESHOLDS["Medium"]:
            return "Medium"
        return "Low"