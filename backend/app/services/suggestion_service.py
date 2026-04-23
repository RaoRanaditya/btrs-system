import logging
from typing import Optional
from sqlalchemy.orm import Session
from app.models.bug import Bug
from app.models.fix_suggestion import FixSuggestion

logger = logging.getLogger(__name__)

WEIGHT_BUG_TYPE = 3
WEIGHT_MODULE = 2
WEIGHT_CATEGORY = 1

class FixSuggestionService:
    def __init__(self, db: Session):
        self.db = db

    def get_suggestions_for_bug(self, bug: Bug) -> list:
        candidates = self.db.query(FixSuggestion).filter(FixSuggestion.is_active == True).all()
        if not candidates:
            return []
        scored = []
        for fix in candidates:
            score = 0
            if fix.bug_type == bug.bug_type:
                score += WEIGHT_BUG_TYPE
            if fix.module == bug.module:
                score += WEIGHT_MODULE
            if fix.category == bug.category:
                score += WEIGHT_CATEGORY
            if score > 0:
                scored.append((score, fix))
        scored.sort(key=lambda x: (-x[0], -x[1].times_applied))
        return [fix for _, fix in scored]
