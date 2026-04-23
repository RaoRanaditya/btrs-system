import logging
from uuid import uuid4
from typing import Optional
from sqlalchemy.orm import Session
from app.models.bug import Bug
from app.models.bug_history import BugHistory
from app.services.classification_service import ClassificationService
from app.services.priority_service import PriorityService

logger = logging.getLogger(__name__)

SEVERITY_MAP = {"low": 1, "medium": 2, "high": 4, "critical": 5}

class BugService:
    def __init__(self, db: Session):
        self.db = db

    def create_bug(self, data: dict) -> Bug:
        category = ClassificationService.classify(data.get("title", ""), data.get("description", ""))
        sev = data.get("severity", "medium")
        sev_int = SEVERITY_MAP.get(str(sev).lower(), 2) if isinstance(sev, str) else int(sev)
        priority_result = PriorityService.compute_priority(
            severity=sev_int,
            impact=data.get("impact", 1),
            frequency=data.get("frequency", 1),
            reproducibility=data.get("reproducibility", 1),
        )
        bug = Bug(
            id=str(uuid4()),
            title=data["title"],
            description=data["description"],
            module=data["module"],
            location=data.get("location", ""),
            bug_type=data.get("bug_type", "unknown"),
            category=category,
            severity=data.get("severity", "medium"),
            frequency=data.get("frequency", 1),
            impact=data.get("impact", 1),
            reproducibility=data.get("reproducibility", 1),
            priority=priority_result.priority,
            priority_score=priority_result.score,
            status="New",
            reported_by=data.get("reported_by"),
        )
        self.db.add(bug)
        self.db.add(BugHistory(id=str(uuid4()), bug_id=bug.id, field_changed="status", old_value=None, new_value="New", change_source="system", notes="Bug created"))
        self.db.commit()
        self.db.refresh(bug)
        return bug

    def get_all_bugs(self, filters: Optional[dict] = None, skip: int = 0, limit: int = 50):
        query = self.db.query(Bug).filter(Bug.is_deleted == False)
        if filters:
            if filters.get("status"):
                query = query.filter(Bug.status == filters["status"])
            if filters.get("priority"):
                query = query.filter(Bug.priority == filters["priority"])
            if filters.get("module"):
                query = query.filter(Bug.module == filters["module"])
            if filters.get("category"):
                query = query.filter(Bug.category == filters["category"])
        total = query.count()
        bugs = query.order_by(Bug.created_at.desc()).offset(skip).limit(limit).all()
        return bugs, total

    def get_bug_by_id(self, bug_id: str) -> Optional[Bug]:
        return self.db.query(Bug).filter(Bug.id == bug_id, Bug.is_deleted == False).first()

    def update_bug(self, bug_id: str, data: dict) -> Bug:
        bug = self.get_bug_by_id(bug_id)
        if not bug:
            raise ValueError(f"Bug '{bug_id}' not found.")
        priority_fields = {"severity", "impact", "frequency", "reproducibility"}
        text_fields = {"title", "description"}
        changed_priority = False
        changed_text = False
        for field, value in data.items():
            if hasattr(bug, field) and getattr(bug, field) != value:
                self.db.add(BugHistory(id=str(uuid4()), bug_id=bug_id, field_changed=field, old_value=str(getattr(bug, field)), new_value=str(value), change_source="user"))
                setattr(bug, field, value)
                if field in priority_fields:
                    changed_priority = True
                if field in text_fields:
                    changed_text = True
        if changed_priority:
            sev = bug.severity
            sev_int = SEVERITY_MAP.get(str(sev).lower(), 2) if isinstance(sev, str) else int(sev)
            result = PriorityService.compute_priority(severity=sev_int, impact=bug.impact, frequency=bug.frequency, reproducibility=bug.reproducibility)
            bug.priority = result.priority
            bug.priority_score = result.score
        if changed_text:
            bug.category = ClassificationService.classify(bug.title, bug.description)
        self.db.commit()
        self.db.refresh(bug)
        return bug

    def delete_bug(self, bug_id: str) -> None:
        bug = self.get_bug_by_id(bug_id)
        if not bug:
            raise ValueError(f"Bug '{bug_id}' not found.")
        bug.is_deleted = True
        self.db.commit()
