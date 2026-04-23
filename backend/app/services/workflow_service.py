"""
Workflow Service
Manages bug status transitions using an explicit state machine.

Valid transitions
-----------------
  New         → Assigned
  Assigned    → In Progress
  In Progress → Resolved
  Resolved    → (terminal — no further transitions allowed)

Any other transition is rejected with a ValueError.
"""

import logging
from datetime import datetime, timezone
from uuid import uuid4
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.models.bug import Bug
from app.models.bug_history import BugHistory

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# State machine definition
# Key   = current status
# Value = set of valid next statuses
# ---------------------------------------------------------------------------
VALID_TRANSITIONS: dict[str, set[str]] = {
    "New":         {"Assigned"},
    "Assigned":    {"In Progress"},
    "In Progress": {"Resolved"},
    "Resolved":    set(),           # terminal state
}

ALL_STATUSES = set(VALID_TRANSITIONS.keys())


class WorkflowService:
    """
    Enforces valid bug status transitions and manages assignee changes.
    """

    # ------------------------------------------------------------------
    # Core transition method
    # ------------------------------------------------------------------
    @staticmethod
    def transition(
        db: Session,
        bug_id: str,
        new_status: str,
        changed_by: str,
        assignee_id: Optional[str] = None,
        resolution_note: Optional[str] = None,
    ) -> Bug:
        """
        Transition a bug to a new status.

        Rules enforced:
          - new_status must be a recognised status string
          - Transition must be valid per VALID_TRANSITIONS
          - Resolved bugs are immutable (terminal state)
          - 'Assigned' transition requires an assignee_id
          - 'Resolved' transition can optionally carry a resolution_note

        Args:
            db              : Active SQLAlchemy session
            bug_id          : UUID of the bug to transition
            new_status      : Target status string
            changed_by      : UUID of the user performing the action
            assignee_id     : UUID of assigned developer (required for → Assigned)
            resolution_note : Free-text note (optional, used when → Resolved)

        Returns:
            Updated Bug ORM object

        Raises:
            ValueError      : On invalid status or forbidden transition
        """
        try:
            # --- Validate target status string ---
            if new_status not in ALL_STATUSES:
                raise ValueError(
                    f"'{new_status}' is not a valid status. "
                    f"Allowed: {sorted(ALL_STATUSES)}"
                )

            bug = WorkflowService._get_bug(db, bug_id)
            current_status = bug.status

            # --- Guard: terminal state ---
            if current_status == "Resolved":
                raise ValueError(
                    f"Bug '{bug_id}' is already Resolved and cannot be transitioned further."
                )

            # --- Guard: no-op ---
            if current_status == new_status:
                raise ValueError(
                    f"Bug '{bug_id}' is already in status '{current_status}'."
                )

            # --- Guard: valid transition ---
            allowed_next = VALID_TRANSITIONS.get(current_status, set())
            if new_status not in allowed_next:
                raise ValueError(
                    f"Transition '{current_status}' → '{new_status}' is not allowed. "
                    f"From '{current_status}', valid next states are: "
                    f"{sorted(allowed_next) or '(none — terminal state)'}."
                )

            # --- Business rules per target status ---
            if new_status == "Assigned":
                if not assignee_id:
                    raise ValueError(
                        "Transitioning to 'Assigned' requires a valid 'assignee_id'."
                    )
                bug.assignee_id = assignee_id

            if new_status == "Resolved":
                bug.resolved_at = datetime.now(timezone.utc)
                if resolution_note:
                    bug.resolution_note = resolution_note

            # --- Apply transition ---
            old_status  = bug.status
            bug.status  = new_status
            bug.updated_at = datetime.now(timezone.utc)

            # --- Audit log ---
            note = resolution_note if new_status == "Resolved" else ""
            WorkflowService._log_history(
                db=db,
                bug_id=bug_id,
                changed_by=changed_by,
                old_value=old_status,
                new_value=new_status,
                note=note or f"Transitioned by user {changed_by}",
            )

            db.commit()
            db.refresh(bug)

            logger.info(
                "Bug workflow transition: id=%s '%s' → '%s' by user=%s",
                bug_id,
                old_status,
                new_status,
                changed_by,
            )
            return bug

        except (SQLAlchemyError, ValueError) as exc:
            db.rollback()
            logger.exception(
                "Workflow transition failed for bug id=%s: %s", bug_id, exc
            )
            raise

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------
    @staticmethod
    def assign(
        db: Session,
        bug_id: str,
        assignee_id: str,
        changed_by: str,
    ) -> Bug:
        """Shorthand: New → Assigned."""
        return WorkflowService.transition(
            db=db,
            bug_id=bug_id,
            new_status="Assigned",
            changed_by=changed_by,
            assignee_id=assignee_id,
        )

    @staticmethod
    def start_progress(
        db: Session,
        bug_id: str,
        changed_by: str,
    ) -> Bug:
        """Shorthand: Assigned → In Progress."""
        return WorkflowService.transition(
            db=db,
            bug_id=bug_id,
            new_status="In Progress",
            changed_by=changed_by,
        )

    @staticmethod
    def resolve(
        db: Session,
        bug_id: str,
        changed_by: str,
        resolution_note: Optional[str] = None,
    ) -> Bug:
        """Shorthand: In Progress → Resolved."""
        return WorkflowService.transition(
            db=db,
            bug_id=bug_id,
            new_status="Resolved",
            changed_by=changed_by,
            resolution_note=resolution_note,
        )

    @staticmethod
    def get_allowed_transitions(current_status: str) -> list[str]:
        """
        Return the list of valid next statuses from a given state.
        Safe to call without a DB session (pure logic).
        """
        if current_status not in VALID_TRANSITIONS:
            raise ValueError(
                f"Unknown status: '{current_status}'. "
                f"Known statuses: {sorted(ALL_STATUSES)}"
            )
        return sorted(VALID_TRANSITIONS[current_status])

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _get_bug(db: Session, bug_id: str) -> Bug:
        bug = db.query(Bug).filter(Bug.id == bug_id).first()
        if not bug:
            raise ValueError(f"Bug with id '{bug_id}' not found.")
        return bug

    @staticmethod
    def _log_history(
        db: Session,
        bug_id: str,
        changed_by: str,
        old_value: str,
        new_value: str,
        note: str = "",
    ) -> None:
        """Append a BugHistory audit row (caller is responsible for commit)."""
        history = BugHistory(
            id=str(uuid4()),
            bug_id=bug_id,
            changed_by=changed_by,
            field_changed="status",
            old_value=old_value,
            new_value=new_value,
            note=note,
            changed_at=datetime.now(timezone.utc),
        )
        db.add(history)