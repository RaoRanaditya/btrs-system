from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

SEVERITY_SCORE = {"low": 1, "medium": 2, "high": 4, "critical": 5}
PRIORITY_WEIGHTS = {"severity": 0.40, "impact": 0.30, "frequency": 0.20, "reproducibility": 0.10}
PRIORITY_THRESHOLDS = {"High": 3.5, "Medium": 2.0}
WORKFLOW_TRANSITIONS = {"New": {"Assigned"}, "Assigned": {"In Progress"}, "In Progress": {"Resolved"}, "Resolved": set()}

CLASSIFICATION_RULES = [
    (["network", "connection", "timeout", "socket", "dns", "http", "https", "api call", "request failed", "unreachable", "refused", "ssl", "tls", "certificate", "proxy", "firewall", "latency", "ping", "offline", "disconnect"], "connectivity", "connectivity"),
    (["database", "db ", " sql", "query", "migration", "schema", "table", "column", "row", "record", "null", "constraint", "foreign key", "primary key", "transaction", "rollback", "commit", "storage", "disk", "file not found", "read error", "write error", "corrupt", "data loss", "cache", "redis", "mongo", "orm"], "data_flow", "data/storage"),
    (["ui", "ux", "render", "layout", "css", "html", "style", "font", "color", "button", "modal", "dropdown", "tooltip", "responsive", "mobile view", "icon", "image not loading", "overlap", "alignment", "scroll", "flickering", "blank screen", "white screen", "dark mode", "theme", "padding", "margin", "z-index", "overflow"], "display", "display"),
    (["import", "module", "class", "inheritance", "interface", "architecture", "dependency", "circular", "refactor", "structure", "package", "namespace", "compile", "build", "syntax", "type error", "attribute error", "missing method", "abstract", "constructor", "destructor", "init", "config", "environment", "setup", "install"], "construction", "structural"),
    (["crash", "exception", "error", "bug", "fail", "broken", "not working", "unexpected", "wrong output", "incorrect", "logic", "calculation", "algorithm", "loop", "condition", "validation", "authentication", "authorization", "permission", "login", "logout", "register", "password", "token", "session", "race condition", "deadlock", "freeze", "hang", "memory leak", "performance", "slow"], "crash", "functional"),
]

@dataclass(frozen=True)
class ClassificationResult:
    bug_type: str
    category: str
    matched_keyword: Optional[str] = None

@dataclass(frozen=True)
class PriorityResult:
    priority: str
    score: float
    breakdown: dict = field(default_factory=dict)

class RuleEngine:
    @staticmethod
    def classify(title: str, description: str = "") -> ClassificationResult:
        if not title and not description:
            return ClassificationResult(bug_type="unknown", category="functional")
        corpus = f"{title} {description}".lower()
        for keywords, bug_type, category in CLASSIFICATION_RULES:
            for kw in keywords:
                if kw in corpus:
                    return ClassificationResult(bug_type=bug_type, category=category, matched_keyword=kw)
        return ClassificationResult(bug_type="unknown", category="functional")

    @staticmethod
    def compute_priority(severity, impact, frequency, reproducibility) -> PriorityResult:
        def clamp(v): return max(1, min(5, int(v)))
        sev_int = SEVERITY_SCORE.get(str(severity).lower(), 2) if isinstance(severity, str) else int(severity)
        raw = {"severity": clamp(sev_int), "impact": clamp(impact), "frequency": clamp(frequency), "reproducibility": clamp(reproducibility)}
        breakdown = {f: round(raw[f] * PRIORITY_WEIGHTS[f], 3) for f in PRIORITY_WEIGHTS}
        score = round(sum(breakdown.values()), 2)
        priority = "High" if score >= PRIORITY_THRESHOLDS["High"] else ("Medium" if score >= PRIORITY_THRESHOLDS["Medium"] else "Low")
        return PriorityResult(priority=priority, score=score, breakdown=breakdown)

    @staticmethod
    def is_valid_transition(current_status: str, new_status: str) -> bool:
        return new_status in WORKFLOW_TRANSITIONS.get(current_status, set())

    @staticmethod
    def allowed_transitions(current_status: str) -> set:
        return WORKFLOW_TRANSITIONS.get(current_status, set())