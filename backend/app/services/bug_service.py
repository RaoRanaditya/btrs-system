import logging
from uuid import uuid4
from typing import Optional
from sqlalchemy.orm import Session
from app.models.bug import Bug
from app.models.bug_history import BugHistory
from app.core.rules import RuleEngine

logger = logging.getLogger(__name__)

class BugService:
    def __init__(self, db: Session):
        self.db = db

    def create_bug(self, data: dict) -> Bug:
        classification = RuleEngine.classify(data.get("title", ""), data.get("description", ""))
        priority_result = RuleEngine.compute_priority(
            severity=data.get("severity", "medium"),
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
            environment=data.get("environment", "production"),
            bug_type=classification.bug_type,
            category=classification.category,
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
        self.db.add(BugHistory(id=str(uuid4()), bug_id=bug.id, field_changed="status", old_value=None, new_value="New", change_source="system", notes="Bug created via rule engine"))
        self.db.commit()
        self.db.refresh(bug)
        return bug

    def get_all_bugs(self, filters: Optional[dict] = None, skip: int = 0, limit: int = 50):
        query = self.db.query(Bug).filter(Bug.is_deleted == False)
        if filters:
            if filters.get("status"): query = query.filter(Bug.status == filters["status"])
            if filters.get("priority"): query = query.filter(Bug.priority == filters["priority"])
            if filters.get("module"): query = query.filter(Bug.module == filters["module"])
            if filters.get("category"): query = query.filter(Bug.category == filters["category"])
        total = query.count()
        bugs = query.order_by(Bug.created_at.desc()).offset(skip).limit(limit).all()
        return bugs, total

    def get_bug_by_id(self, bug_id: str) -> Optional[Bug]:
        return self.db.query(Bug).filter(Bug.id == bug_id, Bug.is_deleted == False).first()

    def update_bug(self, bug_id: str, data: dict) -> Bug:
        bug = self.get_bug_by_id(bug_id)
        if not bug: raise ValueError(f"Bug '{bug_id}' not found.")
        priority_fields = {"severity", "impact", "frequency", "reproducibility"}
        text_fields = {"title", "description"}
        changed_priority = changed_text = False
        for field_name, value in data.items():
            if hasattr(bug, field_name) and getattr(bug, field_name) != value:
                self.db.add(BugHistory(id=str(uuid4()), bug_id=bug_id, field_changed=field_name, old_value=str(getattr(bug, field_name)), new_value=str(value), change_source="user"))
                setattr(bug, field_name, value)
                if field_name in priority_fields: changed_priority = True
                if field_name in text_fields: changed_text = True
        if changed_priority:
            result = RuleEngine.compute_priority(severity=bug.severity, impact=bug.impact, frequency=bug.frequency, reproducibility=bug.reproducibility)
            bug.priority = result.priority
            bug.priority_score = result.score
        if changed_text:
            cl = RuleEngine.classify(bug.title, bug.description)
            bug.bug_type = cl.bug_type
            bug.category = cl.category
        self.db.commit()
        self.db.refresh(bug)
        return bug

    def delete_bug(self, bug_id: str) -> None:
        bug = self.get_bug_by_id(bug_id)
        if not bug: raise ValueError(f"Bug '{bug_id}' not found.")
        bug.is_deleted = True
        self.db.commit()