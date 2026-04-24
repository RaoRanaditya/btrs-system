#!/bin/bash
# ============================================================
# BTRS Fix Script
# Run from: ~/Desktop/btrs-system/backend/
# Usage:    bash fix_btrs.sh
# ============================================================

set -e

BACKEND_DIR="$(cd "$(dirname "$0")" && pwd)"
echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║         BTRS Backend Fix Script              ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
echo "→ Working in: $BACKEND_DIR"
echo ""

# 1. Activate venv if not active
if [ -z "$VIRTUAL_ENV" ]; then
    if [ -f "$BACKEND_DIR/venv/bin/activate" ]; then
        source "$BACKEND_DIR/venv/bin/activate"
        echo "✓ Activated venv"
    else
        echo "✗ No venv found at $BACKEND_DIR/venv — creating one..."
        python3 -m venv venv
        source venv/bin/activate
        echo "✓ Created and activated venv"
    fi
else
    echo "✓ venv already active: $VIRTUAL_ENV"
fi

# 2. Fix requirements.txt
echo ""
echo "→ Writing fixed requirements.txt..."
cat > "$BACKEND_DIR/requirements.txt" << 'EOF'
fastapi>=0.100.0
uvicorn[standard]>=0.22.0
sqlalchemy>=2.0.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
python-dotenv>=1.0.0
EOF
echo "✓ requirements.txt updated"

# 3. Install deps
echo ""
echo "→ Installing dependencies..."
pip install -q -r "$BACKEND_DIR/requirements.txt"
echo "✓ Dependencies installed"

# 4. Fix config.py — the root cause of the crash
echo ""
echo "→ Fixing app/config.py (BaseSettings migration)..."
cat > "$BACKEND_DIR/app/config.py" << 'EOF'
from functools import lru_cache

try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./bugtracker.db"
    DB_ECHO: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
EOF
echo "✓ config.py fixed"

# 5. Fix database.py — connect_args only for SQLite
echo ""
echo "→ Fixing app/database.py..."
cat > "$BACKEND_DIR/app/database.py" << 'EOF'
import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=settings.DB_ECHO,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db: Session = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def db_session() -> Generator[Session, None, None]:
    db: Session = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def check_database_connection() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.error("Database connection FAILED: %s", exc)
        return False


def create_tables() -> None:
    from app.models.user import User
    from app.models.bug import Bug
    from app.models.bug_history import BugHistory
    from app.models.fix_suggestion import FixSuggestion
    Base.metadata.create_all(bind=engine)
    logger.info("All tables created.")
EOF
echo "✓ database.py fixed"

# 6. Fix workflow.py — correct BugHistory field names (no previous_status attr)
echo ""
echo "→ Fixing app/routes/workflow.py (BugHistory field names)..."
cat > "$BACKEND_DIR/app/routes/workflow.py" << 'PYEOF'
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
PYEOF
echo "✓ workflow.py fixed"

# 7. Fix main.py — ensure analytics router is included
echo ""
echo "→ Fixing app/main.py..."
cat > "$BACKEND_DIR/app/main.py" << 'PYEOF'
import logging
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.routes.bugs import router as bugs_router
from app.routes.workflow import router as workflow_router
from app.routes.suggestions import router as suggestions_router
from app.routes.analytics import router as analytics_router

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.database import create_tables
    create_tables()
    logger.info("Bug Tracking API started.")
    yield

app = FastAPI(title="BTRS", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def timing_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Process-Time-ms"] = f"{(time.perf_counter()-start)*1000:.2f}"
    return response


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={
        "success": False, "message": "Validation error",
        "errors": [{"field": "->".join(map(str, e["loc"])), "message": e["msg"]}
                   for e in exc.errors()]})


@app.exception_handler(Exception)
async def global_handler(request: Request, exc: Exception):
    logger.error("Unhandled: %s", exc, exc_info=True)
    return JSONResponse(status_code=500, content={"success": False, "message": "Internal server error"})


app.include_router(bugs_router, prefix="/api/v1")
app.include_router(workflow_router, prefix="/api/v1")
app.include_router(suggestions_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")


@app.get("/health", tags=["System"])
def health():
    from app.database import check_database_connection
    ok = check_database_connection()
    return {"status": "ok" if ok else "degraded", "database": "connected" if ok else "error"}


@app.get("/", tags=["System"])
def root():
    return {"message": "BTRS running", "docs": "/docs"}
PYEOF
echo "✓ main.py fixed"

# 8. Verify analytics route exists
echo ""
if [ -f "$BACKEND_DIR/app/routes/analytics.py" ]; then
    echo "✓ analytics.py already exists"
else
    echo "→ Creating missing analytics.py..."
    cat > "$BACKEND_DIR/app/routes/analytics.py" << 'PYEOF'
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
        return {"total": 0, "resolution_rate": 0, "by_status": {}, "by_priority": {},
                "by_category": {}, "by_severity": {}, "by_bug_type": {}, "top_modules": []}
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
    top_modules = sorted([{"module": m, "count": c} for m, c in module_counts.items()],
                         key=lambda x: -x["count"])[:10]
    return {"total": total, "resolution_rate": resolution_rate, "by_status": by_status,
            "by_priority": by_priority, "by_category": by_category, "by_severity": by_severity,
            "by_bug_type": by_bug_type, "top_modules": top_modules}
PYEOF
    echo "✓ analytics.py created"
fi

# 9. Quick import test
echo ""
echo "→ Testing imports..."
cd "$BACKEND_DIR"
python3 -c "
from app.config import get_settings
from app.database import Base, create_tables
from app.models.bug import Bug
from app.models.bug_history import BugHistory
from app.models.fix_suggestion import FixSuggestion
from app.core.rules import RuleEngine
print('  All imports OK')
s = get_settings()
print(f'  DATABASE_URL = {s.DATABASE_URL}')
r = RuleEngine.classify('login button crash', 'user cannot login')
print(f'  Rule engine OK: bug_type={r.bug_type}, category={r.category}')
" && echo "✓ Import test passed" || echo "✗ Import test FAILED — check output above"

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  All fixes applied!                          ║"
echo "║                                              ║"
echo "║  Start the server:                           ║"
echo "║    uvicorn app.main:app --reload             ║"
echo "║                                              ║"
echo "║  Then open: frontend/index.html              ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
