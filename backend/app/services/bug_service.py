"""
Bug Service
CRUD operations for the Bug model.
Integrates ClassificationService and PriorityService automatically on create/update.
"""

import logging
from uuid import uuid4
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.models.bug import Bug
from app.models.bug_history import BugHistory
from app.services.classification_service import ClassificationService
from app.services.priority_service import PriorityService

logger = logging.getLogger(__name__)


class BugService:
    """
    Encapsulates all bug lifecycle operations.
    Every mutating method also writes a BugHistory record.
    """

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------
    @staticmethod
    def create_bug(
        db: Session,
        title: str,
        description: str,
        reporter_id: str,
        module: str,
        bug_type: str,
        severity: int,
        impact: int,
        frequency: int,
        reproducibility: int,
    ) -> Bug:
        """
        Create a new bug record.

        Auto-assigns:
          - category  (via ClassificationService)
          - priority  (via PriorityService)
          - status    → 'New'
          - uuid      primary key

        Args:
            db               : Active SQLAlchemy session
            title            : Short bug title
            description      : Detailed description
            reporter_id      : UUID of the reporting user
            module           : Application module affected
            bug_type         : Type tag (e.g. 'crash', 'ui_glitch')
            severity         : 1–5
            impact           : 1–5
            frequency        : 1–5
            reproducibility  : 1–5

        Returns:
            Persisted Bug ORM object
        """
        try:
            # --- Classification ---
            category = ClassificationService.classify(title, description)

            # --- Priority ---
            priority_result = PriorityService.compute_priority(
                severity=severity,
                impact=impact,
                frequency=frequency,
                reproducibility=reproducibility,
            )

            bug = Bug(
                id=str(uuid4()),
                title=title,
                description=description,
                reporter_id=reporter_id,
                module=module,
                bug_type=bug_type,
                category=category,
                severity=severity,
                impact=impact,
                frequency=frequency,
                reproducibility=reproducibility,
                priority=priority_result.priority,
                priority_score=priority_result.score,
                status="New",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )

            db.add(bug)

            # --- History entry ---
            BugService._log_history(
                db=db,
                bug_id=bug.id,
                changed_by=reporter_id,
                field_changed="status",
                old_value=None,
                new_value="New",
                note="Bug created",
            )

            db.commit()
            db.refresh(bug)

            logger.info(
                "Bug created: id=%s title='%s' priority=%s category=%s",
                bug.id,
                bug.title,
                bug.priority,
                bug.category,
            )
            return bug

        except (SQLAlchemyError, ValueError) as exc:
            db.rollback()
            logger.exception("Failed to create bug: %s", exc)
            raise

    # ------------------------------------------------------------------
    # READ — all
    # ------------------------------------------------------------------
    @staticmethod
    def get_all_bugs(
        db: Session,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        category: Optional[str] = None,
        module: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Bug]:
        """
        Retrieve bugs with optional filters.

        Args:
            db       : Active SQLAlchemy session
            status   : Filter by status string
            priority : Filter by priority string
            category : Filter by category string
            module   : Filter by module string
            limit    : Max records to return (default 100)
            offset   : Pagination offset (default 0)

        Returns:
            List of Bug ORM objects
        """
        try:
            query = db.query(Bug)

            if status:
                query = query.filter(Bug.status == status)
            if priority:
                query = query.filter(Bug.priority == priority)
            if category:
                query = query.filter(Bug.category == category)
            if module:
                query = query.filter(Bug.module == module)

            bugs = query.order_by(Bug.created_at.desc()).limit(limit).offset(offset).all()

            logger.debug("get_all_bugs returned %d records.", len(bugs))
            return bugs

        except SQLAlchemyError as exc:
            logger.exception("Failed to fetch bugs: %s", exc)
            raise

    # ------------------------------------------------------------------
    # READ — single
    # ------------------------------------------------------------------
    @staticmethod
    def get_bug_by_id(db: Session, bug_id: str) -> Bug:
        """
        Fetch a single bug by its UUID.

        Raises:
            ValueError  : If bug is not found
        """
        try:
            bug = db.query(Bug).filter(Bug.id == bug_id).first()
            if not bug:
                raise ValueError(f"Bug with id '{bug_id}' not found.")
            return bug

        except SQLAlchemyError as exc:
            logger.exception("DB error fetching bug id=%s: %s", bug_id, exc)
            raise

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------
    @staticmethod
    def update_bug(
        db: Session,
        bug_id: str,
        updated_by: str,
        **fields,
    ) -> Bug:
        """
        Update mutable fields of an existing bug.

        Automatically recalculates category and priority when relevant
        fields change. Records each changed field in BugHistory.

        Args:
            db          : Active SQLAlchemy session
            bug_id      : UUID of the bug to update
            updated_by  : UUID of the user performing the update
            **fields    : Keyword args matching Bug model columns

        Returns:
            Updated Bug ORM object
        """
        try:
            bug = BugService.get_bug_by_id(db, bug_id)

            PRIORITY_FACTORS = {"severity", "impact", "frequency", "reproducibility"}
            TEXT_FIELDS       = {"title", "description"}
            MUTABLE_FIELDS    = PRIORITY_FACTORS | TEXT_FIELDS | {
                "module", "bug_type", "assignee_id",
            }

            changed_priority_factor = False
            changed_text = False

            for field, new_value in fields.items():
                if field not in MUTABLE_FIELDS:
                    logger.warning("Ignoring non-mutable field: '%s'", field)
                    continue

                old_value = getattr(bug, field, None)
                if old_value == new_value:
                    continue  # skip unchanged fields

                setattr(bug, field, new_value)

                BugService._log_history(
                    db=db,
                    bug_id=bug_id,
                    changed_by=updated_by,
                    field_changed=field,
                    old_value=str(old_value),
                    new_value=str(new_value),
                )

                if field in PRIORITY_FACTORS:
                    changed_priority_factor = True
                if field in TEXT_FIELDS:
                    changed_text = True

            # --- Recalculate priority if any factor changed ---
            if changed_priority_factor:
                priority_result = PriorityService.compute_priority(
                    severity=bug.severity,
                    impact=bug.impact,
                    frequency=bug.frequency,
                    reproducibility=bug.reproducibility,
                )
                old_priority = bug.priority
                bug.priority       = priority_result.priority
                bug.priority_score = priority_result.score

                if old_priority != bug.priority:
                    BugService._log_history(
                        db=db,
                        bug_id=bug_id,
                        changed_by=updated_by,
                        field_changed="priority",
                        old_value=old_priority,
                        new_value=bug.priority,
                        note="Auto-recalculated",
                    )

            # --- Recalculate category if title/description changed ---
            if changed_text:
                new_category = ClassificationService.classify(
                    bug.title, bug.description
                )
                if new_category != bug.category:
                    BugService._log_history(
                        db=db,
                        bug_id=bug_id,
                        changed_by=updated_by,
                        field_changed="category",
                        old_value=bug.category,
                        new_value=new_category,
                        note="Auto-reclassified",
                    )
                    bug.category = new_category

            bug.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(bug)

            logger.info("Bug updated: id=%s by user=%s", bug_id, updated_by)
            return bug

        except (SQLAlchemyError, ValueError) as exc:
            db.rollback()
            logger.exception("Failed to update bug id=%s: %s", bug_id, exc)
            raise

    # ------------------------------------------------------------------
    # DELETE
    # ------------------------------------------------------------------
    @staticmethod
    def delete_bug(db: Session, bug_id: str, deleted_by: str) -> bool:
        """
        Soft-or-hard delete a bug record.

        Current implementation performs a hard delete and logs the event
        in BugHistory before removal.

        Args:
            db          : Active SQLAlchemy session
            bug_id      : UUID of the bug to delete
            deleted_by  : UUID of the user performing the deletion

        Returns:
            True on success
        """
        try:
            bug = BugService.get_bug_by_id(db, bug_id)

            BugService._log_history(
                db=db,
                bug_id=bug_id,
                changed_by=deleted_by,
                field_changed="status",
                old_value=bug.status,
                new_value="Deleted",
                note="Bug record deleted",
            )

            db.delete(bug)
            db.commit()

            logger.info("Bug deleted: id=%s by user=%s", bug_id, deleted_by)
            return True

        except (SQLAlchemyError, ValueError) as exc:
            db.rollback()
            logger.exception("Failed to delete bug id=%s: %s", bug_id, exc)
            raise

    # ------------------------------------------------------------------
    # INTERNAL HELPER
    # ------------------------------------------------------------------
    @staticmethod
    def _log_history(
        db: Session,
        bug_id: str,
        changed_by: str,
        field_changed: str,
        old_value: Optional[str],
        new_value: Optional[str],
        note: str = "",
    ) -> None:
        """Insert a BugHistory audit row (does NOT commit — caller commits)."""
        history = BugHistory(
            id=str(uuid4()),
            bug_id=bug_id,
            changed_by=changed_by,
            field_changed=field_changed,
            old_value=old_value,
            new_value=new_value,
            note=note,
            changed_at=datetime.now(timezone.utc),
        )
        db.add(history)