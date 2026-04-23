"""
core/scoring.py
───────────────
Isolated scoring logic referenced throughout the paper.

Paper section 6.3:
  "The combination of severities and the frequency of occurrence determine
   the urgency. Each bug's attributes — severity, frequency, impact, and
   consistency — are assigned a score, and each score can be adjusted with
   a multiplier to determine a value."

This module exposes a single function-style interface so the service layer
can import scoring without depending on the full RuleEngine.
"""

from __future__ import annotations
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

SEVERITY_MAP: dict[str, int] = {
    "low":      1,
    "medium":   2,
    "high":     4,
    "critical": 5,
}

# Weights must sum to 1.0
WEIGHTS: dict[str, float] = {
    "severity":        0.40,
    "impact":          0.30,
    "frequency":       0.20,
    "reproducibility": 0.10,
}

# Score thresholds (inclusive lower bound)
THRESHOLDS: dict[str, float] = {
    "High":   3.5,
    "Medium": 2.0,
    # everything below Medium threshold → "Low"
}

# Valid input range for all numeric factors
MIN_FACTOR = 1
MAX_FACTOR = 5      # severity scale; 1–10 inputs are mapped to 1–5


# ─────────────────────────────────────────────────────────────────────────────
# DATA CLASS
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ScoringResult:
    priority: str        # "High" | "Medium" | "Low"
    score: float         # composite weighted score
    breakdown: dict      # {factor: weighted_contribution}
    raw_inputs: dict     # {factor: clamped_value} — for auditability


# ─────────────────────────────────────────────────────────────────────────────
# SCORING FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def _clamp(value: int, lo: int = MIN_FACTOR, hi: int = MAX_FACTOR) -> int:
    """Clamp value to [lo, hi]."""
    return max(lo, min(hi, int(value)))


def _severity_to_int(severity: str | int) -> int:
    """Convert severity label to integer or pass through integer."""
    if isinstance(severity, int):
        return severity
    return SEVERITY_MAP.get(str(severity).lower(), 2)


def compute_score(
    severity: str | int,
    impact: int,
    frequency: int,
    reproducibility: int,
) -> ScoringResult:
    """
    Compute a weighted priority score for a bug.

    All inputs are normalised to [1, 5] before weighting.
    Scores on 1–10 range (from the UI) map naturally since clamp(v, 1, 5)
    handles values > 5 by capping them — preserving relative order.

    Args:
        severity        : "low"|"medium"|"high"|"critical" or int 1-5
        impact          : int 1-10  (user-entered)
        frequency       : int 1-10  (user-entered)
        reproducibility : int 1-10  (user-entered)

    Returns:
        ScoringResult with priority label, composite score, and per-factor breakdown.
    """
    sev_int = _severity_to_int(severity)

    raw = {
        "severity":        _clamp(sev_int),
        "impact":          _clamp(impact),
        "frequency":       _clamp(frequency),
        "reproducibility": _clamp(reproducibility),
    }

    breakdown = {
        factor: round(raw[factor] * WEIGHTS[factor], 3)
        for factor in WEIGHTS
    }

    score = round(sum(breakdown.values()), 2)

    if score >= THRESHOLDS["High"]:
        priority = "High"
    elif score >= THRESHOLDS["Medium"]:
        priority = "Medium"
    else:
        priority = "Low"

    logger.debug(
        "Scoring → score=%.2f priority=%s raw=%s breakdown=%s",
        score, priority, raw, breakdown,
    )

    return ScoringResult(
        priority=priority,
        score=score,
        breakdown=breakdown,
        raw_inputs=raw,
    )


def severity_label_from_score(score: float) -> str:
    """Utility: map a composite score back to a human priority label."""
    if score >= THRESHOLDS["High"]:
        return "High"
    if score >= THRESHOLDS["Medium"]:
        return "Medium"
    return "Low"


def explain_score(result: ScoringResult) -> str:
    """
    Return a human-readable explanation of a scoring result.
    Paper emphasis: 'nothing is opaque', 'clear process'.
    """
    lines = [
        f"Priority: {result.priority}  (score: {result.score:.2f})",
        "",
        "Factor breakdown:",
    ]
    for factor, contribution in result.breakdown.items():
        raw = result.raw_inputs[factor]
        weight_pct = int(WEIGHTS[factor] * 100)
        lines.append(
            f"  {factor:<18} raw={raw}  weight={weight_pct}%  "
            f"contribution={contribution:.3f}"
        )
    lines += [
        "",
        f"Threshold  High≥{THRESHOLDS['High']}  Medium≥{THRESHOLDS['Medium']}  Low<{THRESHOLDS['Medium']}",
    ]
    return "\n".join(lines)