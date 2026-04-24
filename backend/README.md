# BTRS — Bug Tracking & Resolution System

Rule-based bug tracking backend built with FastAPI + MySQL.
Zero ML — pure Python keyword rules and weighted scoring.

---

## Project Structure

```
backend/
├── app/
│   ├── main.py                        # App entry point
│   ├── config.py                      # Settings from .env
│   ├── database.py                    # SQLAlchemy engine + session
│   │
│   ├── core/
│   │   ├── rules.py                   # Keyword classification rules
│   │   └── scoring.py                 # Priority weight constants
│   │
│   ├── models/
│   │   ├── base_model.py              # UUID PK + timestamps mixin
│   │   ├── user.py
│   │   ├── bug.py                     # All bug enums + Bug model
│   │   ├── bug_history.py             # Audit trail (immutable)
│   │   └── fix_suggestion.py          # Historical fix knowledge base
│   │
│   ├── schemas/
│   │   ├── common.py                  # SuccessResponse, PaginatedResponse
│   │   ├── bug.py                     # Bug request/response schemas
│   │   └── fix_suggestion.py          # Suggestion schemas
│   │
│   ├── services/
│   │   ├── bug_service.py             # CRUD + auto classify + auto score
│   │   ├── classification_service.py  # Keyword rule engine
│   │   ├── priority_service.py        # Weighted scoring formula
│   │   ├── suggestion_service.py      # 3-tier historical fix matcher
│   │   └── workflow_service.py        # FSM state transitions
│   │
│   ├── routes/
│   │   ├── bugs.py                    # CRUD endpoints
│   │   ├── workflow.py                # Assign + status endpoints
│   │   └── suggestions.py             # Fix suggestion endpoints
│   │
│   └── utils/
│       ├── logger.py                  # Rotating file + console logging
│       └── exceptions.py             # Custom exception hierarchy
│
├── schema.sql                         # MySQL CREATE TABLE script
├── requirements.txt
├── .env                               # Your local config (never commit)
└── .env.example                       # Template
```

---

## Step-by-Step Setup

### 1. Clone / place the project

```bash
cd backend/
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set your MySQL credentials:

```
DB_HOST=localhost
DB_PORT=3306
DB_NAME=btrs_db
DB_USER=root
DB_PASSWORD=your_actual_password
```

### 5. Create the MySQL database and tables

Open MySQL Workbench (or any MySQL client) and run:

```
schema.sql   ← paste the entire file and execute
```

This creates `btrs_db`, all 4 tables, indexes, and seeds 8 fix suggestions.

### 6. Run the server

```bash
uvicorn app.main:app --reload
```

The API is now live at: **http://localhost:8000**

---

## API Reference

Interactive docs: **http://localhost:8000/docs**

### Bug Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| POST   | `/api/v1/bugs`                  | Create bug (auto-classify + auto-score) |
| GET    | `/api/v1/bugs`                  | List bugs (paginated, filterable) |
| GET    | `/api/v1/bugs/{id}`             | Get bug by ID |
| PUT    | `/api/v1/bugs/{id}`             | Update bug (re-classifies if text changes) |
| DELETE | `/api/v1/bugs/{id}`             | Soft-delete (never hard-deleted) |
| GET    | `/api/v1/bugs/{id}/history`     | Full audit trail |

### Workflow Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| POST   | `/api/v1/bugs/{id}/assign`      | Assign bug to a developer |
| POST   | `/api/v1/bugs/{id}/status`      | Advance FSM status |
| GET    | `/api/v1/bugs/workflow/transitions` | Show valid FSM transition map |

### Suggestion Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| GET    | `/api/v1/suggestions/{bug_id}`                          | Get fix suggestions (3-tier match) |
| POST   | `/api/v1/suggestions/{bug_id}/applied/{suggestion_id}`  | Mark suggestion as applied |
| POST   | `/api/v1/suggestions/{bug_id}/seed`                     | Seed new fix into knowledge base |

### System

| Method | URL | Description |
|--------|-----|-------------|
| GET    | `/`        | API info |
| GET    | `/health`  | DB connectivity check |

---

## Example: Create a Bug

```bash
curl -X POST http://localhost:8000/api/v1/bugs \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Login button does not respond on Safari",
    "description": "Users clicking the login button get no response. No error in console.",
    "module": "auth",
    "location": "/login page",
    "bug_type": "functional",
    "severity": "high",
    "frequency": "always",
    "impact": "critical",
    "reproducibility": "always",
    "environment": "production"
  }'
```

The system will automatically:
1. Classify the bug (keyword match → `functional`)
2. Score priority: `(75×0.35) + (100×0.25) + (100×0.25) + (100×0.15)` = **91.25 → HIGH**
3. Set status to `new`
4. Log a creation history entry

---

## Priority Scoring Formula

```
score = (severity_score  × 0.35)
      + (frequency_score × 0.25)
      + (impact_score    × 0.25)
      + (repro_score     × 0.15)

Scores:  critical=100  high=75  medium=50  low=25
Repro:   always=100  sometimes=66  rarely=33  not_reproducible=0

Thresholds:
  score ≥ 70  →  HIGH
  score ≥ 40  →  MEDIUM
  score <  40  →  LOW
```

## FSM Workflow

```
new  →  assigned  →  in_progress  →  resolved
```
No skipping. No reversing. Every transition is logged to `bug_history`.