import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

WEIGHTS = {"severity": 0.40, "impact": 0.30, "frequency": 0.20, "reproducibility": 0.10}
THRESHOLDS = {"High": 3.5, "Medium": 2.0}

@dataclass(frozen=True)
class PriorityResult:
    priority: str
    score: float

class PriorityService:
    @staticmethod
    def compute_priority(severity: int, impact: int, frequency: int, reproducibility: int) -> PriorityResult:
        def clamp(v): return max(1, min(5, int(v)))
        score = round(
            clamp(severity) * WEIGHTS["severity"] +
            clamp(impact) * WEIGHTS["impact"] +
            clamp(frequency) * WEIGHTS["frequency"] +
            clamp(reproducibility) * WEIGHTS["reproducibility"], 2)
        priority = "High" if score >= THRESHOLDS["High"] else ("Medium" if score >= THRESHOLDS["Medium"] else "Low")
        return PriorityResult(priority=priority, score=score)
