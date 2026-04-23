import logging
from uuid import uuid4
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from app.models.bug import Bug
from app.models.bug_history import BugHistory

logger = logging.getLogger(__name__)

VALID_TRANSITIONS = {
    "New": {"Assigned"},
    "Assigned": {"In Progress"},
    "In Progress": {"Resolved"},
    "Resolved": set(),
}

class WorkflowService:
    def __init__(self, db: Session):
        self.db = db

    def _get_bug(self, bug_id: str) -> Bug:
        bug = self.db.query(Bug).filter(Bug.id == bug_id).first()
        if not bug:
            raise ValueError(f"Bug '{bug_id}' not found.")
        return bug

    def _log(self, bug_id, old, new, note=""):
        self.db.add(BugHistory(id=str(uuid4()), bug_id=bug_id, field_changed="status", old_value=old, new_value=new, change_source="user", notes=note))

    def assign_bug(self, bug_id: str, assigned_to: str, note: Optional[str] = None) -> Bug:
        bug = self._get_bug(bug_id)
        if "Assigned" not in VALID_TRANSITIONS.get(bug.status, set()):
            raise ValueError(f"Cannot assign bug in status '{bug.status}'.")
        old = bug.status
        bug.status = "Assigned"
        bug.assigned_to = assigned_to
        self._log(bug_id, old, "Assigned", note or "")
        self.db.commit()
        self.db.refresh(bug)
        return bug

    def transition_status(self, bug_id: str, new_status: str, note: Optional[str] = None) -> Bug:
        bug = self._get_bug(bug_id)
        allowed = VALID_TRANSITIONS.get(bug.status, set())
        if new_status not in allowed:
            raise ValueError(f"Transition '{bug.status}' → '{new_status}' not allowed. Allowed: {sorted(allowed) or '(none)'}")
        old = bug.status
        bug.status = new_status
        if new_status == "Resolved":
            bug.resolved_at = datetime.now(timezone.utc)
        self._log(bug_id, old, new_status, note or "")
        self.db.commit()
        self.db.refresh(bug)
        return bug

    def get_history(self, bug_id: str):
        return self.db.query(BugHistory).filter(BugHistory.bug_id == bug_id).order_by(BugHistory.created_at.desc()).all()
