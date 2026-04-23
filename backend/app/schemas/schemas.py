from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class BugStatus(str, Enum):
    NEW = "New"
    ASSIGNED = "Assigned"
    IN_PROGRESS = "In Progress"
    RESOLVED = "Resolved"

class BugSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class BugCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: str = Field(..., min_length=10)
    module: str = Field(..., max_length=100)
    severity: BugSeverity = Field(default=BugSeverity.MEDIUM)
    frequency: int = Field(default=1, ge=1, le=10)
    impact: int = Field(default=1, ge=1, le=10)
    reproducibility: int = Field(default=1, ge=1, le=10)
    reported_by: Optional[str] = Field(None, max_length=100)
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
    bug_type: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    status: str
    assigned_to: Optional[str] = None
    reported_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True

class BugListResponse(BaseModel):
    total: int
    bugs: List[BugResponse]

class AssignBugRequest(BaseModel):
    assigned_to: str = Field(..., min_length=2, max_length=100)
    note: Optional[str] = Field(None, max_length=500)

class UpdateStatusRequest(BaseModel):
    status: BugStatus = Field(...)
    note: Optional[str] = Field(None, max_length=500)
    class Config:
        use_enum_values = True

class WorkflowResponse(BaseModel):
    bug_id: str
    previous_status: str
    current_status: str
    message: str

class FixSuggestionResponse(BaseModel):
    id: str
    source_bug_id: Optional[str] = None
    bug_type: str
    module: str
    category: str
    problem_summary: str
    fix_description: str
    confidence_score: float
    times_applied: int
    created_at: datetime
    class Config:
        from_attributes = True

class SuggestionsListResponse(BaseModel):
    bug_id: str
    total: int
    suggestions: List[FixSuggestionResponse]

class MessageResponse(BaseModel):
    message: str
    success: bool = True
