"""
routes/suggestions.py
---------------------
FastAPI route handlers for fix suggestions.
Delegates matching logic entirely to FixSuggestionService.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import SuggestionsListResponse, FixSuggestionResponse
from app.services.bug_service import BugService
from app.services.fix_suggestion_service import FixSuggestionService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/suggestions",
    tags=["Fix Suggestions"],
)


# ─────────────────────────────────────────────
# GET /suggestions/{bug_id}
# ─────────────────────────────────────────────

@router.get(
    "/{bug_id}",
    response_model=SuggestionsListResponse,
    summary="Get fix suggestions for a bug",
    description=(
        "Returns ranked fix suggestions by querying past **resolved** bugs "
        "that share the same `bug_type`, `module`, or `category`. "
        "Matching is entirely rule-based — no ML involved."
    ),
)
def get_suggestions(
    bug_id: str,
    limit: int = Query(5, ge=1, le=20, description="Maximum suggestions to return"),
    db: Session = Depends(get_db),
):
    """
    Fetch fix suggestions:

    - **bug_id**: The bug you want suggestions for.
    - **limit**: Cap on returned suggestions (default 5).

    Suggestions are ranked by match confidence:
    `exact` > `partial` > `category_only`.
    """
    # ── 1. Confirm the bug exists ──────────────────────────────────────
    bug_service = BugService(db)
    bug = bug_service.get_bug_by_id(bug_id)
    if not bug:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bug with ID '{bug_id}' not found.",
        )

    # ── 2. Delegate to suggestion service ─────────────────────────────
    try:
        suggestion_service = FixSuggestionService(db)
        suggestions = suggestion_service.get_suggestions(bug_id, limit=limit)

        logger.info(
            "Returned %d suggestion(s) for bug %s.", len(suggestions), bug_id
        )

        return SuggestionsListResponse(
            bug_id=bug_id,
            total=len(suggestions),
            suggestions=[
                FixSuggestionResponse(
                    id=str(s.id),
                    bug_id=str(s.bug_id),
                    suggested_fix=s.suggested_fix,
                    matched_on=s.matched_on,
                    confidence=s.confidence,
                    source_bug_title=s.source_bug_title,
                    created_at=s.created_at,
                )
                for s in suggestions
            ],
        )

    except Exception as exc:
        logger.error(
            "Error fetching suggestions for bug %s: %s", bug_id, exc, exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve fix suggestions.",
        )


# ─────────────────────────────────────────────
# GET /suggestions/{bug_id}/best
# ─────────────────────────────────────────────

@router.get(
    "/{bug_id}/best",
    response_model=FixSuggestionResponse,
    summary="Get the single best fix suggestion",
    description=(
        "Returns only the highest-confidence fix suggestion for the bug. "
        "Returns HTTP 404 when no suggestions are available."
    ),
)
def get_best_suggestion(
    bug_id: str,
    db: Session = Depends(get_db),
):
    # ── 1. Confirm the bug exists ──────────────────────────────────────
    bug_service = BugService(db)
    bug = bug_service.get_bug_by_id(bug_id)
    if not bug:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bug with ID '{bug_id}' not found.",
        )

    # ── 2. Fetch top suggestion ────────────────────────────────────────
    try:
        suggestion_service = FixSuggestionService(db)
        suggestions = suggestion_service.get_suggestions(bug_id, limit=1)

        if not suggestions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    f"No fix suggestions found for bug '{bug_id}'. "
                    "Resolve similar bugs first to build the suggestion database."
                ),
            )

        best = suggestions[0]
        logger.info("Best suggestion for bug %s: confidence=%s", bug_id, best.confidence)

        return FixSuggestionResponse(
            id=str(best.id),
            bug_id=str(best.bug_id),
            suggested_fix=best.suggested_fix,
            matched_on=best.matched_on,
            confidence=best.confidence,
            source_bug_title=best.source_bug_title,
            created_at=best.created_at,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Error fetching best suggestion for bug %s: %s", bug_id, exc, exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve best fix suggestion.",
        )