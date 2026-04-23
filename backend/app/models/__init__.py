# ============================================================
# models/__init__.py
# Exports every model and enum from a single import point.
#
# Why this matters:
#   SQLAlchemy's relationship() uses string-based forward refs
#   (e.g. "Bug", "User"). For those refs to resolve correctly,
#   ALL models must be imported before any relationship is
#   accessed. Importing this package guarantees that.
#
# Usage anywhere in the app:
#   from app.models import Bug, User, BugHistory, FixSuggestion
#   from app.models import StatusEnum, SeverityEnum
# ============================================================

from app.models.user import User
from app.models.bug import (
    Bug,
    BugTypeEnum,
    CategoryEnum,
    SeverityEnum,
    FrequencyEnum,
    ImpactEnum,
    ReproducibilityEnum,
    PriorityLevelEnum,
    StatusEnum,
)
from app.models.bug_history import BugHistory, ChangeSourceEnum
from app.models.fix_suggestion import FixSuggestion

__all__ = [
    # Models
    "User",
    "Bug",
    "BugHistory",
    "FixSuggestion",
    # Bug enums
    "BugTypeEnum",
    "CategoryEnum",
    "SeverityEnum",
    "FrequencyEnum",
    "ImpactEnum",
    "ReproducibilityEnum",
    "PriorityLevelEnum",
    "StatusEnum",
    # History enums
    "ChangeSourceEnum",
]