"""
routes/workflow.py — Paper section 6.5
FSM: New → Assigned → In Progress → Resolved
BugHistory correct fields: old_value, new_value, notes, created_at
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.schemas import AssignBugRequest, UpdateStatusRequest, WorkflowResponse
from app.services.bug_service import BugService
from app.services.workflow_service import WorkflowService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/bugs", tags=["Workflow"])


def _get_bug_or_404(bug_id: str, db: Session):
    bug = BugService(db).get_bug_by_id(bug_id)
    if not bug:
        raise HTTPException(status_code=404, detail=f"Bug '{bug_id}' not found.")
    return bug


@router.post("/{bug_id}/assign", response_model=WorkflowResponse)
def assign_bug(bug_id: str, payload: AssignBugRequest, db: Session = Depends(get_db)):
    bug = _get_bug_or_404(bug_id, db)
    try:
        previous = bug.status
        updated = WorkflowService(db).assign_bug(bug_id, payload.assigned_to, payload.note)
        return WorkflowResponse(bug_id=bug_id, previous_status=previous,
                                current_status=updated.status,
                                message=f"Assigned to '{payload.assigned_to}'.")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except Exception as exc:
        logger.error("Assign error %s: %s", bug_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to assign bug.")


@router.post("/{bug_id}/status", response_model=WorkflowResponse)
def update_status(bug_id: str, payload: UpdateStatusRequest, db: Session = Depends(get_db)):
    bug = _get_bug_or_404(bug_id, db)
    try:
        previous = bug.status
        updated = WorkflowService(db).transition_status(bug_id, payload.status, payload.note)
        return WorkflowResponse(bug_id=bug_id, previous_status=previous,
                                current_status=updated.status,
                                message=f"Status → '{updated.status}'.")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except Exception as exc:
        logger.error("Status error %s: %s", bug_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update status.")


@router.get("/{bug_id}/history")
def get_bug_history(bug_id: str, db: Session = Depends(get_db)):
    _get_bug_or_404(bug_id, db)
    try:
        history = WorkflowService(db).get_history(bug_id)
        return {
            "bug_id": bug_id,
            "total": len(history),
            "history": [
                {
                    "id": str(h.id),
                    "field_changed": h.field_changed,
                    "old_value": h.old_value,
                    "new_value": h.new_value,
                    "changed_by": h.changed_by,
                    "change_source": h.change_source,
                    "notes": h.notes,
                    "changed_at": h.created_at.isoformat() if h.created_at else None,
                }
                for h in history
            ],
        }
    except Exception as exc:
        logger.error("History error %s: %s", bug_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch history.")


@router.get("/workflow/transitions")
def get_transitions():
    from app.core.rules import WORKFLOW_TRANSITIONS
    return {"transitions": {k: sorted(v) for k, v in WORKFLOW_TRANSITIONS.items()}}
