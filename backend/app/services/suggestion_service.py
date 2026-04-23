# """
# Suggestion Service
# Rule-based fix suggestion engine.
# Queries historical resolved bugs and ranks candidates by match specificity.

# Match scoring (additive, deterministic):
#   bug_type  exact match  →  +3  (strongest signal)
#   module    exact match  →  +2
#   category  exact match  →  +1
#   fallback  any resolved →   0  (returned when no match at all)
# """

# import logging
# from dataclasses import dataclass
# from typing import Optional

# from sqlalchemy.orm import Session
# from sqlalchemy.exc import SQLAlchemyError

# from app.models.bug import Bug
# from app.models.fix_suggestion import FixSuggestion

# logger = logging.getLogger(__name__)


# @dataclass(frozen=True)
# class SuggestionResult:
#     found: bool
#     score: int                       # match specificity score
#     suggestion: Optional[str]        # fix text
#     source_bug_id: Optional[str]     # which resolved bug this came from
#     match_reason: str                # human-readable explanation


# # Match weights — change here, logic stays untouched
# WEIGHT_BUG_TYPE = 3
# WEIGHT_MODULE   = 2
# WEIGHT_CATEGORY = 1


# class SuggestionService:
#     """
#     Provides fix suggestions by matching the current bug against
#     historically resolved bugs and stored FixSuggestion records.
#     """

#     @staticmethod
#     def get_suggestion(
#         db: Session,
#         bug_type: str,
#         module: str,
#         category: str,
#     ) -> SuggestionResult:
#         """
#         Find the best-matching fix suggestion for a bug.

#         Strategy (in order of preference):
#           1. Score all resolved bugs by field overlap → pick highest score
#           2. If tie → prefer most recently resolved
#           3. Return their associated FixSuggestion text
#           4. If nothing found → return a no-suggestion result

#         Args:
#             db       : Active SQLAlchemy session
#             bug_type : Bug type tag of the current bug
#             module   : Module of the current bug
#             category : Category of the current bug

#         Returns:
#             SuggestionResult dataclass
#         """
#         try:
#             # Fetch all resolved bugs that have at least one matching field
#             resolved_bugs: list[Bug] = (
#                 db.query(Bug)
#                 .filter(
#                     Bug.status == "Resolved",
#                     Bug.bug_type.in_([bug_type]),          # broadened below
#                 )
#                 .order_by(Bug.updated_at.desc())
#                 .all()
#             )

#             # Broaden: also pull by module or category if the above is empty
#             if not resolved_bugs:
#                 resolved_bugs = (
#                     db.query(Bug)
#                     .filter(
#                         Bug.status == "Resolved",
#                     )
#                     .order_by(Bug.updated_at.desc())
#                     .limit(200)         # cap scan for performance
#                     .all()
#                 )

#             if not resolved_bugs:
#                 logger.info(
#                     "No resolved bugs found for suggestion (type=%s, module=%s, category=%s).",
#                     bug_type, module, category,
#                 )
#                 return SuggestionResult(
#                     found=False,
#                     score=0,
#                     suggestion=None,
#                     source_bug_id=None,
#                     match_reason="No resolved bugs in the system yet.",
#                 )

#             # --- Score each candidate ---
#             best_score    = -1
#             best_bug: Optional[Bug] = None

#             for candidate in resolved_bugs:
#                 score = 0
#                 if candidate.bug_type == bug_type:
#                     score += WEIGHT_BUG_TYPE
#                 if candidate.module == module:
#                     score += WEIGHT_MODULE
#                 if candidate.category == category:
#                     score += WEIGHT_CATEGORY

#                 if score > best_score:
#                     best_score = score
#                     best_bug   = candidate

#             if best_bug is None or best_score == 0:
#                 return SuggestionResult(
#                     found=False,
#                     score=0,
#                     suggestion=None,
#                     source_bug_id=None,
#                     match_reason=(
#                         "No resolved bug matched on bug_type, module, or category."
#                     ),
#                 )

#             # --- Fetch fix suggestion tied to the winning resolved bug ---
#             fix: Optional[FixSuggestion] = (
#                 db.query(FixSuggestion)
#                 .filter(FixSuggestion.bug_id == best_bug.id)
#                 .order_by(FixSuggestion.created_at.desc())
#                 .first()
#             )

#             if not fix:
#                 # Best match found but no fix text recorded yet
#                 return SuggestionResult(
#                     found=False,
#                     score=best_score,
#                     suggestion=None,
#                     source_bug_id=best_bug.id,
#                     match_reason=(
#                         f"Closest resolved bug found (score={best_score}) "
#                         f"but no fix suggestion text is recorded."
#                     ),
#                 )

#             # Build a readable explanation of why this was chosen
#             reasons = []
#             if best_bug.bug_type == bug_type:
#                 reasons.append(f"bug_type='{bug_type}'")
#             if best_bug.module == module:
#                 reasons.append(f"module='{module}'")
#             if best_bug.category == category:
#                 reasons.append(f"category='{category}'")

#             match_reason = (
#                 f"Matched on: {', '.join(reasons)} (score={best_score})"
#                 if reasons
#                 else f"Partial match (score={best_score})"
#             )

#             logger.info(
#                 "Suggestion found: source_bug=%s score=%d reason='%s'",
#                 best_bug.id,
#                 best_score,
#                 match_reason,
#             )

#             return SuggestionResult(
#                 found=True,
#                 score=best_score,
#                 suggestion=fix.suggestion_text,
#                 source_bug_id=best_bug.id,
#                 match_reason=match_reason,
#             )

#         except SQLAlchemyError as exc:
#             logger.exception("DB error in get_suggestion: %s", exc)
#             raise

# app/routes/suggestions.py

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.bug_service import BugService
from app.services.suggestion_service import SuggestionService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/suggestions",
    tags=["Suggestions"],
)


# ─────────────────────────────────────────────
# GET /suggestions/{bug_id}
# ─────────────────────────────────────────────
@router.get("/{bug_id}")
def get_suggestion_for_bug(
    bug_id: str,
    db: Session = Depends(get_db),
):
    try:
        # Step 1: Get bug
        bug = BugService.get_bug_by_id(db, bug_id)

        # Step 2: Get suggestion using YOUR service
        result = SuggestionService.get_suggestion(
            db=db,
            bug_type=bug.bug_type,
            module=bug.module,
            category=bug.category,
        )

        # Step 3: Format response
        return {
            "bug_id": bug_id,
            "found": result.found,
            "score": result.score,
            "suggestion": result.suggestion,
            "source_bug_id": result.source_bug_id,
            "match_reason": result.match_reason,
        }

    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(ve),
        )

    except Exception as exc:
        logger.error(
            "Error fetching suggestion for bug %s: %s",
            bug_id,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch suggestion.",
        )