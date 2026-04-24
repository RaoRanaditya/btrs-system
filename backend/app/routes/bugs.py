import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.schemas import BugCreate, BugUpdate, BugResponse, BugListResponse, MessageResponse
from app.services.bug_service import BugService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bugs", tags=["Bugs"])


@router.post("/", response_model=BugResponse, status_code=status.HTTP_201_CREATED)
def create_bug(payload: BugCreate, db: Session = Depends(get_db)):
    try:
        service = BugService(db)
        bug = service.create_bug(payload.dict())
        return bug
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.error("Error creating bug: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create bug.")


@router.get("/", response_model=BugListResponse)
def list_bugs(
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    module: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    try:
        service = BugService(db)
        filters = {k: v for k, v in {"status": status, "priority": priority, "module": module, "category": category}.items() if v}
        bugs, total = service.get_all_bugs(filters=filters, skip=skip, limit=limit)
        return BugListResponse(total=total, bugs=bugs)
    except Exception as exc:
        logger.error("Error listing bugs: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list bugs.")


@router.get("/{bug_id}", response_model=BugResponse)
def get_bug(bug_id: str, db: Session = Depends(get_db)):
    service = BugService(db)
    bug = service.get_bug_by_id(bug_id)
    if not bug:
        raise HTTPException(status_code=404, detail=f"Bug '{bug_id}' not found.")
    return bug


@router.put("/{bug_id}", response_model=BugResponse)
def update_bug(bug_id: str, payload: BugUpdate, db: Session = Depends(get_db)):
    service = BugService(db)
    if not service.get_bug_by_id(bug_id):
        raise HTTPException(status_code=404, detail=f"Bug '{bug_id}' not found.")
    data = payload.dict(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=422, detail="No fields provided for update.")
    try:
        return service.update_bug(bug_id, data)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.error("Error updating bug: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update bug.")


@router.delete("/{bug_id}", response_model=MessageResponse)
def delete_bug(bug_id: str, db: Session = Depends(get_db)):
    service = BugService(db)
    if not service.get_bug_by_id(bug_id):
        raise HTTPException(status_code=404, detail=f"Bug '{bug_id}' not found.")
    service.delete_bug(bug_id)
    return MessageResponse(message=f"Bug '{bug_id}' deleted successfully.")