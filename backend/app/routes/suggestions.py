# app/routes/suggestions.py

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.schemas import SuggestionsListResponse
from app.services.bug_service import BugService
from app.services.suggestion_service import FixSuggestionService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/suggestions",
    tags=["Suggestions"],
)


# ─────────────────────────────────────────────
# GET /suggestions/{bug_id}
# ─────────────────────────────────────────────
@router.get(
    "/{bug_id}",
    response_model=SuggestionsListResponse,
    summary="Get fix suggestions for a bug",
    description=(
        "Returns ranked fix suggestions by matching past resolved bugs "
        "based on bug_type, module, and category."
    ),
)
def get_suggestions(
    bug_id: str,
    db: Session = Depends(get_db),
):
    try:
        bug_service = BugService(db)
        suggestion_service = FixSuggestionService(db)

        # Step 1: Check if bug exists
        bug = bug_service.get_bug_by_id(bug_id)
        if not bug:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bug with ID '{bug_id}' not found.",
            )

        # Step 2: Get suggestions
        suggestions = suggestion_service.get_suggestions_for_bug(bug)

        return {
            "bug_id": bug_id,
            "total": len(suggestions),
            "suggestions": suggestions,
        }

    except HTTPException:
        raise

    except Exception as exc:
        logger.error(
            "Error fetching suggestions for bug %s: %s",
            bug_id,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch suggestions.",
        )