"""
services/classification_service.py
------------------------------------
Thin wrapper — delegates to RuleEngine (core/rules.py).
Paper section 6.2: rule-based bug classification.
Kept for backwards compatibility with any code that imports ClassificationService.
"""
from app.core.rules import RuleEngine


class ClassificationService:
    @staticmethod
    def classify(title: str, description: str = "") -> str:
        """Returns category string. Delegates to RuleEngine."""
        result = RuleEngine.classify(title, description)
        return result.category

    @staticmethod
    def classify_full(title: str, description: str = ""):
        """Returns full ClassificationResult (bug_type + category)."""
        return RuleEngine.classify(title, description)

    @staticmethod
    def get_all_categories() -> list[str]:
        from app.core.rules import CLASSIFICATION_RULES
        return list({cat for _, _, cat in CLASSIFICATION_RULES})