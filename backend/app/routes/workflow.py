"""
routes/workflow.py
------------------
FastAPI route handlers for bug workflow / state-machine transitions.
All transition logic lives in WorkflowService — this layer only wires
HTTP → service → HTTP response.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.schemas import (
    AssignBugRequest,
    UpdateStatusRequest,
    WorkflowResponse,
    BugResponse,
)
from app.services.bug_service import BugService
from app.services.workflow_service import WorkflowService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/bugs",
    tags=["Workflow"],
)


# ─────────────────────────────────────────────
# Helper — resolve bug or raise 404
# ─────────────────────────────────────────────

def _get_bug_or_404(bug_id: str, db: Session):
    """Fetch bug; raise HTTP 404 when not found."""
    service = BugService(db)
    bug = service.get_bug_by_id(bug_id)
    if not bug:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bug with ID '{bug_id}' not found.",
        )
    return bug


# ─────────────────────────────────────────────
# POST /bugs/{id}/assign  — Assign bug to a person
# ─────────────────────────────────────────────

@router.post(
    "/{bug_id}/assign",
    response_model=WorkflowResponse,
    status_code=status.HTTP_200_OK,
    summary="Assign bug to a user",
    description=(
        "Assigns the bug to a team member. "
        "Valid only when the bug is in **new** status. "
        "Automatically transitions status to **assigned**."
    ),
)
def assign_bug(
    bug_id: str,
    payload: AssignBugRequest,
    db: Session = Depends(get_db),
):
    """
    Assign a bug:

    - **assigned_to**: Email or username of the assignee.
    - **note**: Optional note logged to bug history.
    """
    bug = _get_bug_or_404(bug_id, db)

    try:
        workflow = WorkflowService(db)
        previous_status = bug.status
        updated_bug = workflow.assign_bug(
            bug_id=bug_id,
            assigned_to=payload.assigned_to,
            note=payload.note,
        )
        logger.info("Bug %s assigned to %s.", bug_id, payload.assigned_to)
        return WorkflowResponse(
            bug_id=bug_id,
            previous_status=previous_status,
            current_status=updated_bug.status,
            message=f"Bug successfully assigned to '{payload.assigned_to}'.",
        )

    except ValueError as exc:
        # WorkflowService raises ValueError for invalid transitions
        logger.warning("Workflow transition rejected for bug %s: %s", bug_id, exc)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error("Error assigning bug %s: %s", bug_id, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to assign bug.",
        )


# ─────────────────────────────────────────────
# POST /bugs/{id}/status  — Update bug status
# ─────────────────────────────────────────────

@router.post(
    "/{bug_id}/status",
    response_model=WorkflowResponse,
    status_code=status.HTTP_200_OK,
    summary="Update bug status",
    description=(
        "Transitions the bug through the workflow: "
        "**new → assigned → in_progress → resolved**. "
        "Invalid transitions are rejected with HTTP 409."
    ),
)
def update_status(
    bug_id: str,
    payload: UpdateStatusRequest,
    db: Session = Depends(get_db),
):
    """
    Update bug status:

    - **status**: Target status (new | assigned | in_progress | resolved).
    - **note**: Optional audit note recorded in bug history.
    """
    bug = _get_bug_or_404(bug_id, db)

    try:
        workflow = WorkflowService(db)
        previous_status = bug.status
        updated_bug = workflow.transition_status(
            bug_id=bug_id,
            new_status=payload.status,
            note=payload.note,
        )
        logger.info(
            "Bug %s status changed: %s → %s.",
            bug_id, previous_status, updated_bug.status,
        )
        return WorkflowResponse(
            bug_id=bug_id,
            previous_status=previous_status,
            current_status=updated_bug.status,
            message=f"Bug status updated to '{updated_bug.status}'.",
        )

    except ValueError as exc:
        logger.warning("Invalid status transition for bug %s: %s", bug_id, exc)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error("Error updating status for bug %s: %s", bug_id, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update bug status.",
        )


# ─────────────────────────────────────────────
# GET /bugs/{id}/history  — Audit trail (bonus)
# ─────────────────────────────────────────────

@router.get(
    "/{bug_id}/history",
    summary="Get bug history / audit trail",
    description="Returns all workflow transitions and notes for a bug, ordered newest-first.",
)
def get_bug_history(
    bug_id: str,
    db: Session = Depends(get_db),
):
    _get_bug_or_404(bug_id, db)

    try:
        workflow = WorkflowService(db)
        history = workflow.get_history(bug_id)
        return {
            "bug_id": bug_id,
            "total": len(history),
            "history": [
                {
                    "id": str(h.id),
                    "changed_by": h.changed_by,
                    "previous_status": h.previous_status,
                    "new_status": h.new_status,
                    "note": h.note,
                    "changed_at": h.changed_at,
                }
                for h in history
            ],
        }
    except Exception as exc:
        logger.error("Error fetching history for bug %s: %s", bug_id, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve bug history.",
        )