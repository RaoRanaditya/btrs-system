"""
schemas.py
----------
Pydantic request/response models for the Bug Tracking API.
"""

from pydantic import BaseModel, Field, UUID4
from typing import Optional, List
from datetime import datetime
from enum import Enum


# ─────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────

class BugStatus(str, Enum):
    NEW = "new"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"


class BugSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PriorityLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


# ─────────────────────────────────────────────
# Bug Schemas
# ─────────────────────────────────────────────

class BugCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=255, example="Login button unresponsive")
    description: str = Field(..., min_length=10, example="Clicking the login button does nothing on mobile browsers.")
    module: str = Field(..., max_length=100, example="authentication")
    severity: BugSeverity = Field(..., example="high")
    frequency: int = Field(..., ge=1, le=10, description="How often bug occurs (1–10)", example=7)
    impact: int = Field(..., ge=1, le=10, description="Business/user impact (1–10)", example=8)
    reproducibility: int = Field(..., ge=1, le=10, description="How easily reproducible (1–10)", example=9)
    reported_by: Optional[str] = Field(None, max_length=100, example="john.doe@example.com")

    class Config:
        use_enum_values = True


class BugUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = Field(None, min_length=10)
    module: Optional[str] = Field(None, max_length=100)
    severity: Optional[BugSeverity] = None
    frequency: Optional[int] = Field(None, ge=1, le=10)
    impact: Optional[int] = Field(None, ge=1, le=10)
    reproducibility: Optional[int] = Field(None, ge=1, le=10)

    class Config:
        use_enum_values = True


class BugResponse(BaseModel):
    id: str
    title: str
    description: str
    module: str
    severity: str
    frequency: int
    impact: int
    reproducibility: int
    bug_type: Optional[str]
    category: Optional[str]
    priority: Optional[str]
    status: str
    assigned_to: Optional[str]
    reported_by: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BugListResponse(BaseModel):
    total: int
    bugs: List[BugResponse]


# ─────────────────────────────────────────────
# Workflow Schemas
# ─────────────────────────────────────────────

class AssignBugRequest(BaseModel):
    assigned_to: str = Field(..., min_length=2, max_length=100, example="jane.smith@example.com")
    note: Optional[str] = Field(None, max_length=500, example="Assigned to mobile team.")


class UpdateStatusRequest(BaseModel):
    status: BugStatus = Field(..., example="in_progress")
    note: Optional[str] = Field(None, max_length=500, example="Started investigation.")

    class Config:
        use_enum_values = True


class WorkflowResponse(BaseModel):
    bug_id: str
    previous_status: str
    current_status: str
    message: str


# ─────────────────────────────────────────────
# Fix Suggestion Schemas
# ─────────────────────────────────────────────

class FixSuggestionResponse(BaseModel):
    id: str
    bug_id: str
    suggested_fix: str
    matched_on: str
    confidence: str
    source_bug_title: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class SuggestionsListResponse(BaseModel):
    bug_id: str
    total: int
    suggestions: List[FixSuggestionResponse]


# ─────────────────────────────────────────────
# Generic Response
# ─────────────────────────────────────────────

class MessageResponse(BaseModel):
    message: str
    success: bool = True