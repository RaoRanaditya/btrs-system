"""
routes/bugs.py
--------------
FastAPI route handlers for Bug CRUD operations.
Delegates all business logic to the service layer.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.schemas import (
    BugCreate,
    BugUpdate,
    BugResponse,
    BugListResponse,
    MessageResponse,
)
from app.services.bug_service import BugService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/bugs",
    tags=["Bugs"],
)


# ─────────────────────────────────────────────
# POST /bugs  — Create a new bug
# ─────────────────────────────────────────────

@router.post(
    "/",
    response_model=BugResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new bug",
    description=(
        "Creates a bug record. "
        "Category and priority are automatically computed by the rule engine."
    ),
)
def create_bug(
    payload: BugCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new bug.

    - **title**: Short descriptive title.
    - **description**: Full bug description (used for classification).
    - **module**: Application module where the bug was found.
    - **severity**: low | medium | high | critical.
    - **frequency / impact / reproducibility**: Scores 1–10 used for priority calculation.
    """
    try:
        service = BugService(db)
        bug = service.create_bug(payload.dict())
        logger.info("Bug created successfully: %s", bug.id)
        return bug
    except ValueError as exc:
        logger.warning("Validation error creating bug: %s", exc)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except Exception as exc:
        logger.error("Unexpected error creating bug: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating the bug.",
        )


# ─────────────────────────────────────────────
# GET /bugs  — List all bugs
# ─────────────────────────────────────────────

@router.get(
    "/",
    response_model=BugListResponse,
    summary="List all bugs",
    description="Returns a paginated list of bugs with optional filters.",
)
def list_bugs(
    status: Optional[str] = Query(None, description="Filter by status (new, assigned, in_progress, resolved)"),
    priority: Optional[str] = Query(None, description="Filter by priority (High, Medium, Low)"),
    module: Optional[str] = Query(None, description="Filter by module name"),
    category: Optional[str] = Query(None, description="Filter by category"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=200, description="Maximum records to return"),
    db: Session = Depends(get_db),
):
    try:
        service = BugService(db)
        filters = {
            k: v for k, v in {
                "status": status,
                "priority": priority,
                "module": module,
                "category": category,
            }.items()
            if v is not None
        }
        bugs, total = service.get_all_bugs(filters=filters, skip=skip, limit=limit)
        return BugListResponse(total=total, bugs=bugs)
    except Exception as exc:
        logger.error("Error fetching bug list: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve bug list.",
        )


# ─────────────────────────────────────────────
# GET /bugs/{id}  — Get single bug
# ─────────────────────────────────────────────

@router.get(
    "/{bug_id}",
    response_model=BugResponse,
    summary="Get a bug by ID",
)
def get_bug(
    bug_id: str,
    db: Session = Depends(get_db),
):
    try:
        service = BugService(db)
        bug = service.get_bug_by_id(bug_id)
        if not bug:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bug with ID '{bug_id}' not found.",
            )
        return bug
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error fetching bug %s: %s", bug_id, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve bug.",
        )


# ─────────────────────────────────────────────
# PUT /bugs/{id}  — Update a bug
# ─────────────────────────────────────────────

@router.put(
    "/{bug_id}",
    response_model=BugResponse,
    summary="Update bug details",
    description=(
        "Partial update — only supplied fields are modified. "
        "Priority and category are recalculated automatically when relevant fields change."
    ),
)
def update_bug(
    bug_id: str,
    payload: BugUpdate,
    db: Session = Depends(get_db),
):
    try:
        service = BugService(db)

        # Confirm bug exists before attempting update
        existing = service.get_bug_by_id(bug_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bug with ID '{bug_id}' not found.",
            )

        update_data = payload.dict(exclude_unset=True)
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No fields provided for update.",
            )

        updated_bug = service.update_bug(bug_id, update_data)
        logger.info("Bug %s updated successfully.", bug_id)
        return updated_bug

    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except Exception as exc:
        logger.error("Error updating bug %s: %s", bug_id, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update bug.",
        )


# ─────────────────────────────────────────────
# DELETE /bugs/{id}  — Delete a bug
# ─────────────────────────────────────────────

@router.delete(
    "/{bug_id}",
    response_model=MessageResponse,
    summary="Delete a bug",
    description="Permanently deletes a bug and its history from the system.",
)
def delete_bug(
    bug_id: str,
    db: Session = Depends(get_db),
):
    try:
        service = BugService(db)

        existing = service.get_bug_by_id(bug_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bug with ID '{bug_id}' not found.",
            )

        service.delete_bug(bug_id)
        logger.info("Bug %s deleted.", bug_id)
        return MessageResponse(message=f"Bug '{bug_id}' has been deleted successfully.")

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error deleting bug %s: %s", bug_id, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete bug.",
        )