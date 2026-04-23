"""
Classification Service
Rule-based bug classification using keyword mapping.
Categories: structural | functional | data/storage | display | connectivity
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Keyword → Category mapping (ordered from most-specific to least-specific)
# Each entry is (keyword_list, category_string).
# The classifier iterates in order; first match wins.
# ---------------------------------------------------------------------------
CLASSIFICATION_RULES: list[tuple[list[str], str]] = [
    # --- connectivity ---
    (
        [
            "network", "connection", "timeout", "socket", "dns",
            "http", "https", "api call", "request failed", "unreachable",
            "refused", "ssl", "tls", "certificate", "proxy", "firewall",
            "latency", "ping", "offline", "disconnect",
        ],
        "connectivity",
    ),
    # --- data/storage ---
    (
        [
            "database", "db", "sql", "query", "migration", "schema",
            "table", "column", "row", "record", "null", "constraint",
            "foreign key", "primary key", "index", "transaction",
            "rollback", "commit", "storage", "disk", "file not found",
            "read error", "write error", "corrupt", "data loss",
            "cache", "redis", "mongo", "orm",
        ],
        "data/storage",
    ),
    # --- display ---
    (
        [
            "ui", "ux", "render", "layout", "css", "html", "style",
            "font", "color", "button", "modal", "dropdown", "tooltip",
            "responsive", "mobile view", "desktop view", "icon",
            "image not loading", "overlap", "alignment", "scroll",
            "flickering", "blank screen", "white screen", "dark mode",
            "theme", "padding", "margin", "z-index", "overflow",
        ],
        "display",
    ),
    # --- structural ---
    (
        [
            "import", "module", "class", "inheritance", "interface",
            "architecture", "dependency", "circular", "refactor",
            "structure", "package", "namespace", "compile", "build",
            "syntax", "type error", "attribute error", "missing method",
            "abstract", "constructor", "destructor", "init", "config",
            "environment", "setup", "install",
        ],
        "structural",
    ),
    # --- functional ---
    (
        [
            "crash", "exception", "error", "bug", "fail", "broken",
            "not working", "unexpected", "wrong output", "incorrect",
            "logic", "calculation", "algorithm", "loop", "condition",
            "validation", "authentication", "authorization", "permission",
            "login", "logout", "register", "password", "token",
            "session", "race condition", "deadlock", "freeze", "hang",
            "memory leak", "performance", "slow", "timeout",
        ],
        "functional",
    ),
]

DEFAULT_CATEGORY = "functional"


class ClassificationService:
    """
    Classifies a bug into a category using deterministic keyword matching.
    Input  : bug title and/or description (plain strings)
    Output : category string
    """

    @staticmethod
    def classify(title: str, description: str = "") -> str:
        """
        Classify a bug based on its title and description.

        Args:
            title       : Bug title (required)
            description : Bug description (optional but improves accuracy)

        Returns:
            Category string: 'structural' | 'functional' |
                             'data/storage' | 'display' | 'connectivity'
        """
        if not title and not description:
            logger.warning("classify() called with empty title and description.")
            return DEFAULT_CATEGORY

        # Normalise to lowercase for case-insensitive matching
        corpus = f"{title} {description}".lower()

        for keywords, category in CLASSIFICATION_RULES:
            for keyword in keywords:
                if keyword in corpus:
                    logger.debug(
                        "Bug classified as '%s' (matched keyword: '%s')",
                        category,
                        keyword,
                    )
                    return category

        logger.debug(
            "No keyword matched for title='%s'. Defaulting to '%s'.",
            title,
            DEFAULT_CATEGORY,
        )
        return DEFAULT_CATEGORY

    @staticmethod
    def get_all_categories() -> list[str]:
        """Return the full list of supported categories."""
        return list({cat for _, cat in CLASSIFICATION_RULES})