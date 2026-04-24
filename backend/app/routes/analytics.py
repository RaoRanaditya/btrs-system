import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.bug import Bug

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/summary")
def get_analytics_summary(db: Session = Depends(get_db)):
    bugs = db.query(Bug).filter(Bug.is_deleted == False).all()
    if not bugs:
        return {"total": 0, "resolution_rate": 0, "by_status": {}, "by_priority": {}, "by_category": {}, "by_severity": {}, "by_bug_type": {}, "top_modules": []}
    total = len(bugs)
    resolved = sum(1 for b in bugs if b.status == "Resolved")
    resolution_rate = round((resolved / total) * 100) if total else 0
    by_status, by_priority, by_category, by_severity, by_bug_type, module_counts = {}, {}, {}, {}, {}, {}
    for b in bugs:
        by_status[b.status] = by_status.get(b.status, 0) + 1
        by_priority[b.priority] = by_priority.get(b.priority, 0) + 1
        by_category[b.category or "uncategorized"] = by_category.get(b.category or "uncategorized", 0) + 1
        by_severity[b.severity] = by_severity.get(b.severity, 0) + 1
        by_bug_type[b.bug_type or "unknown"] = by_bug_type.get(b.bug_type or "unknown", 0) + 1
        module_counts[b.module] = module_counts.get(b.module, 0) + 1
    top_modules = sorted([{"module": m, "count": c} for m, c in module_counts.items()], key=lambda x: -x["count"])[:10]
    return {"total": total, "resolution_rate": resolution_rate, "by_status": by_status, "by_priority": by_priority, "by_category": by_category, "by_severity": by_severity, "by_bug_type": by_bug_type, "top_modules": top_modules}