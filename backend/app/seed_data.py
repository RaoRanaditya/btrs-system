"""
seed_data.py
────────────
Populates the Historical Fix Database with pre-loaded fixes.

Paper section IV:
  "It comes preloaded with a history of resolved bugs, including one for each
   that contains a description of the problem, and a record of the solution.
   When a new issue is entered, the system searches for previous issues based
   on possibly relevant criteria."

Run once:
    python seed_data.py

Or import and call seed() from your startup code.
"""

import logging
import sys
import os

# Allow running from project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# SEED FIXES
# Each entry mirrors the FixSuggestion model:
#   bug_type, module, category, problem_summary, fix_description, fix_tags
# ─────────────────────────────────────────────────────────────────────────────

SEED_FIXES = [
    # ── Authentication / Functional ───────────────────────────────────────────
    {
        "bug_type": "execution_crash",
        "module": "auth",
        "category": "functional",
        "problem_summary": "Login fails with 500 error when password contains special characters",
        "fix_description": (
            "Ensure the password field is properly URL-encoded before hashing. "
            "Use `urllib.parse.quote_plus` on the raw input, or switch to a "
            "constant-time comparison library like `bcrypt.checkpw()` which handles "
            "raw bytes. Also validate that the database column length (VARCHAR) can "
            "accommodate bcrypt hash output (60 chars minimum)."
        ),
        "fix_tags": "auth,password,encoding,bcrypt",
        "confidence_score": 0.92,
    },
    {
        "bug_type": "functional",
        "module": "auth",
        "category": "functional",
        "problem_summary": "Session token expires too quickly — users logged out unexpectedly",
        "fix_description": (
            "Increase SESSION_LIFETIME in config (default was 15 min, set to 8h for "
            "desktop users). Implement sliding expiry — refresh the token timestamp on "
            "each authenticated request. Add a `Remember Me` checkbox that extends "
            "lifetime to 30 days using a persistent cookie."
        ),
        "fix_tags": "auth,session,token,expiry",
        "confidence_score": 0.88,
    },
    {
        "bug_type": "functional",
        "module": "auth",
        "category": "functional",
        "problem_summary": "User registration fails silently when email already exists",
        "fix_description": (
            "Add a unique constraint on the `email` column if not present. "
            "Catch `IntegrityError` from SQLAlchemy and return HTTP 409 Conflict "
            "with a clear message: 'An account with this email already exists.' "
            "Never expose whether an email exists in a security-sensitive context — "
            "consider returning a generic message and sending a notification email instead."
        ),
        "fix_tags": "auth,registration,email,duplicate",
        "confidence_score": 0.90,
    },

    # ── Database / Data Flow ──────────────────────────────────────────────────
    {
        "bug_type": "data_flow",
        "module": "database",
        "category": "data/storage",
        "problem_summary": "Query returns None instead of empty list for no-result searches",
        "fix_description": (
            "Replace `.first()` with `.all()` when expecting a list result. "
            "SQLAlchemy `.first()` returns None when no row matches; `.all()` returns []. "
            "Add a null-guard in the service layer: `return result or []`. "
            "Update API response schema so the `data` field is always an array."
        ),
        "fix_tags": "database,orm,query,null",
        "confidence_score": 0.95,
    },
    {
        "bug_type": "data_flow",
        "module": "database",
        "category": "data/storage",
        "problem_summary": "Database migration fails when adding a NOT NULL column to existing table",
        "fix_description": (
            "When adding a NOT NULL column to a table with existing rows, you must "
            "provide a default value. In Alembic: `op.add_column('table', "
            "sa.Column('col', sa.String(), nullable=False, server_default=''))`. "
            "After migration, remove the server_default if it's not needed permanently. "
            "Always test migrations on a copy of production data first."
        ),
        "fix_tags": "database,migration,alembic,schema",
        "confidence_score": 0.91,
    },
    {
        "bug_type": "data_flow",
        "module": "bugs",
        "category": "data/storage",
        "problem_summary": "Bug records not persisting after commit — rolled back silently",
        "fix_description": (
            "Ensure `db.commit()` is called after all `db.add()` operations. "
            "Wrap the entire create operation in a try/except — if any step fails, "
            "call `db.rollback()`. Check for pending transactions using "
            "`db.in_transaction()`. If using SQLAlchemy's `autocommit=False`, every "
            "write needs an explicit commit."
        ),
        "fix_tags": "database,commit,rollback,transaction",
        "confidence_score": 0.93,
    },

    # ── UI / Display ──────────────────────────────────────────────────────────
    {
        "bug_type": "display",
        "module": "frontend",
        "category": "display",
        "problem_summary": "Bug list table overflows on mobile screens — horizontal scroll appears",
        "fix_description": (
            "Add `overflow-x: auto` on the table wrapper div. Hide lower-priority "
            "columns on small screens using `@media (max-width: 600px) { th:nth-child(n+4) "
            "{ display: none; } }`. Consider switching to a card layout below 480px. "
            "Use `table-layout: fixed` with explicit column widths on desktop."
        ),
        "fix_tags": "ui,responsive,mobile,css,table",
        "confidence_score": 0.87,
    },
    {
        "bug_type": "display",
        "module": "frontend",
        "category": "display",
        "problem_summary": "Modal does not close when clicking outside on iOS Safari",
        "fix_description": (
            "iOS Safari does not fire `click` events on non-interactive elements. "
            "Add `cursor: pointer` to the overlay div, or switch the event listener "
            "to `touchend`. Alternatively attach the close handler to `mousedown` "
            "instead of `click`. Test with `pointer-events: all` on the overlay."
        ),
        "fix_tags": "ui,modal,ios,safari,events",
        "confidence_score": 0.84,
    },
    {
        "bug_type": "display",
        "module": "dashboard",
        "category": "display",
        "problem_summary": "Statistics counters show stale data after bug is resolved",
        "fix_description": (
            "The dashboard stats are computed from a cached copy of `allBugs`. "
            "After any status-changing operation, call `loadBugs()` to refresh the "
            "in-memory array, then call `renderDashboard()`. If performance is a "
            "concern, emit a server-sent event or use polling every 30s."
        ),
        "fix_tags": "ui,dashboard,cache,stats,refresh",
        "confidence_score": 0.89,
    },

    # ── Network / Connectivity ────────────────────────────────────────────────
    {
        "bug_type": "connectivity",
        "module": "api",
        "category": "connectivity",
        "problem_summary": "CORS error when frontend calls backend API from different port",
        "fix_description": (
            "Add the frontend origin to FastAPI's CORS middleware: "
            "`allow_origins=['http://localhost:3000', 'http://localhost:5500']`. "
            "For development, use `allow_origins=['*']` temporarily. "
            "In production, specify exact origins and set "
            "`allow_credentials=True` only if cookies are used."
        ),
        "fix_tags": "api,cors,network,fastapi",
        "confidence_score": 0.96,
    },
    {
        "bug_type": "connectivity",
        "module": "api",
        "category": "connectivity",
        "problem_summary": "API requests timeout after 30 seconds under heavy load",
        "fix_description": (
            "Add async background processing for expensive operations using "
            "FastAPI's `BackgroundTasks`. Increase uvicorn worker count: "
            "`uvicorn app.main:app --workers 4`. Add a request timeout middleware "
            "that returns 408 instead of hanging. Profile slow DB queries with "
            "`EXPLAIN ANALYZE` and add missing indexes."
        ),
        "fix_tags": "api,timeout,performance,async,workers",
        "confidence_score": 0.82,
    },

    # ── Construction / Structural ─────────────────────────────────────────────
    {
        "bug_type": "construction",
        "module": "backend",
        "category": "structural",
        "problem_summary": "Circular import error between models and services",
        "fix_description": (
            "Move shared type definitions to a `schemas.py` or `types.py` module "
            "that neither models nor services import from each other. "
            "Use TYPE_CHECKING guard for type hints: "
            "`from __future__ import annotations` + "
            "`if TYPE_CHECKING: from app.models.bug import Bug`. "
            "Restructure so services import models, but models never import services."
        ),
        "fix_tags": "python,imports,circular,architecture",
        "confidence_score": 0.91,
    },
    {
        "bug_type": "construction",
        "module": "backend",
        "category": "structural",
        "problem_summary": "Environment variables not loaded — app uses hardcoded defaults",
        "fix_description": (
            "Install `python-dotenv` and call `load_dotenv()` at the top of `main.py` "
            "before any other imports. Create a `.env` file (add to .gitignore). "
            "Use Pydantic's `BaseSettings` for type-safe config loading: "
            "`class Settings(BaseSettings): DATABASE_URL: str`. "
            "Validate required vars at startup — fail fast with a clear message."
        ),
        "fix_tags": "config,environment,dotenv,pydantic",
        "confidence_score": 0.94,
    },

    # ── Workflow / Bug Lifecycle ──────────────────────────────────────────────
    {
        "bug_type": "functional",
        "module": "workflow",
        "category": "functional",
        "problem_summary": "Status transition skips 'Assigned' state — goes New → In Progress directly",
        "fix_description": (
            "Enforce the FSM in `WorkflowService.transition_status()`. "
            "The VALID_TRANSITIONS dict must have `'New': {'Assigned'}` only. "
            "Any attempt to jump states should raise `ValueError` and return HTTP 409. "
            "Add a unit test for each invalid transition to prevent regressions."
        ),
        "fix_tags": "workflow,fsm,status,transition",
        "confidence_score": 0.97,
    },
    {
        "bug_type": "functional",
        "module": "workflow",
        "category": "functional",
        "problem_summary": "Bug history not recorded when status is updated via API",
        "fix_description": (
            "After every `bug.status = new_status` assignment, create a `BugHistory` "
            "record with `field_changed='status'`, `old_value=previous_status`, "
            "`new_value=new_status`, and `change_source='user'`. "
            "Commit both the bug update and the history entry in the same transaction "
            "to ensure atomicity."
        ),
        "fix_tags": "workflow,history,audit,status",
        "confidence_score": 0.93,
    },

    # ── Priority / Scoring ────────────────────────────────────────────────────
    {
        "bug_type": "functional",
        "module": "bugs",
        "category": "functional",
        "problem_summary": "Priority not recalculated when severity is updated",
        "fix_description": (
            "In `BugService.update_bug()`, check if any priority-affecting fields "
            "were in the update payload (severity, impact, frequency, reproducibility). "
            "If yes, call `PriorityService.compute_priority()` with the new values "
            "and save `bug.priority` and `bug.priority_score`. "
            "Log the change in BugHistory."
        ),
        "fix_tags": "priority,scoring,update,service",
        "confidence_score": 0.90,
    },

    # ── Fix Suggestion System ─────────────────────────────────────────────────
    {
        "bug_type": "data_flow",
        "module": "suggestions",
        "category": "data/storage",
        "problem_summary": "Fix suggestions not returned — empty list despite matching bugs in DB",
        "fix_description": (
            "Check that `FixSuggestion.is_active` is True for seed records. "
            "Verify the matching criteria: bug_type, module, and category must all "
            "be set on both the bug and the fix suggestion. "
            "Add a fallback: if no exact match, return suggestions matching only "
            "category. Log the match attempt for debugging."
        ),
        "fix_tags": "suggestions,matching,fix,database",
        "confidence_score": 0.88,
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# SEED FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def seed(db=None, force: bool = False):
    """
    Insert seed fix suggestions into the database.

    Args:
        db    : SQLAlchemy Session (created automatically if None)
        force : If True, re-seed even if fixes already exist
    """
    from app.database import SessionLocal, create_tables
    from app.models.fix_suggestion import FixSuggestion
    import uuid

    create_tables()

    if db is None:
        db = SessionLocal()
        _close = True
    else:
        _close = False

    try:
        existing = db.query(FixSuggestion).count()
        if existing > 0 and not force:
            logger.info("Historical fix database already has %d entries. Skipping seed.", existing)
            print(f"[SEED] Skipped — {existing} fixes already in database. Use force=True to re-seed.")
            return

        if force:
            db.query(FixSuggestion).delete()
            db.commit()
            print("[SEED] Cleared existing fix suggestions.")

        for entry in SEED_FIXES:
            fix = FixSuggestion(
                id=str(uuid.uuid4()),
                source_bug_id=None,
                bug_type=entry["bug_type"],
                module=entry["module"],
                category=entry["category"],
                problem_summary=entry["problem_summary"],
                fix_description=entry["fix_description"],
                fix_tags=entry.get("fix_tags", ""),
                times_applied=0,
                confidence_score=entry.get("confidence_score", 1.0),
                is_active=True,
            )
            db.add(fix)

        db.commit()
        print(f"[SEED] ✓ Inserted {len(SEED_FIXES)} historical fix suggestions into the database.")
        logger.info("Seeded %d fix suggestions.", len(SEED_FIXES))

    except Exception as exc:
        db.rollback()
        logger.error("Seed failed: %s", exc, exc_info=True)
        print(f"[SEED] ✗ Seed failed: {exc}")
        raise
    finally:
        if _close:
            db.close()


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    force_reseed = "--force" in sys.argv
    seed(force=force_reseed)