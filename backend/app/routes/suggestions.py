import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.schemas import SuggestionsListResponse, FixSuggestionResponse
from app.services.bug_service import BugService
from app.services.suggestion_service import FixSuggestionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/suggestions", tags=["Suggestions"])


@router.get("/{bug_id}", response_model=SuggestionsListResponse)
def get_suggestions(bug_id: str, db: Session = Depends(get_db)):
    bug = BugService(db).get_bug_by_id(bug_id)
    if not bug:
        raise HTTPException(status_code=404, detail=f"Bug '{bug_id}' not found.")

    try:
        suggestions = FixSuggestionService(db).get_suggestions_for_bug(bug)
        return SuggestionsListResponse(
            bug_id=bug_id,
            total=len(suggestions),
            suggestions=suggestions,
        )
    except Exception as exc:
        logger.error("Error fetching suggestions: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch suggestions.")