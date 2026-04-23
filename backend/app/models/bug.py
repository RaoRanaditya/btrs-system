# # ============================================================
# # models/bug.py
# # Core entity. One row = one reported bug.
# # Fields map directly to paper Section 6.1 report format.
# # ============================================================

# import enum
# from datetime import datetime
# from typing import Optional

# from sqlalchemy import (
#     DateTime,
#     Enum as SAEnum,
#     ForeignKey,
#     Index,
#     Numeric,
#     String,
#     Text,
#     Boolean,
# )
# from sqlalchemy.orm import Mapped, mapped_column, relationship

# from app.models.base_model import BaseModel


# # ============================================================
# # Python Enums — used by SQLAlchemy SAEnum columns.
# # Defining them here keeps the allowed values in one place;
# # both the ORM and Pydantic schemas import from here.
# # ============================================================

# class BugTypeEnum(str, enum.Enum):
#     """
#     Reporter-provided bug type.
#     The classification engine may override/confirm this.
#     """
#     STRUCTURAL   = "structural"
#     FUNCTIONAL   = "functional"
#     DATA_STORAGE = "data_storage"
#     DISPLAY      = "display"
#     CONNECTIVITY = "connectivity"
#     UNKNOWN      = "unknown"


# class CategoryEnum(str, enum.Enum):
#     """
#     Category assigned by the rule-based classification engine
#     (Section 6.2). Derived from keyword matching, not the reporter.
#     """
#     STRUCTURAL    = "structural"
#     FUNCTIONAL    = "functional"
#     DATA_STORAGE  = "data_storage"
#     DISPLAY       = "display"
#     CONNECTIVITY  = "connectivity"
#     UNCATEGORIZED = "uncategorized"


# class SeverityEnum(str, enum.Enum):
#     """
#     Reporter-provided severity. Weight: critical=100, high=75,
#     medium=50, low=25. Used in the priority scoring formula.
#     """
#     CRITICAL = "critical"
#     HIGH     = "high"
#     MEDIUM   = "medium"
#     LOW      = "low"


# class FrequencyEnum(str, enum.Enum):
#     """
#     How often the bug occurs. Weight: always=100, frequent=75,
#     occasional=50, rare=25. Used in priority scoring.
#     """
#     ALWAYS     = "always"
#     FREQUENT   = "frequent"
#     OCCASIONAL = "occasional"
#     RARE       = "rare"


# class ImpactEnum(str, enum.Enum):
#     """
#     Business / user impact level. Weight mirrors SeverityEnum.
#     Used in priority scoring.
#     """
#     CRITICAL = "critical"
#     HIGH     = "high"
#     MEDIUM   = "medium"
#     LOW      = "low"


# class ReproducibilityEnum(str, enum.Enum):
#     """
#     Can another developer reproduce this bug?
#     always=100, sometimes=66, rarely=33, not_reproducible=0.
#     """
#     ALWAYS           = "always"
#     SOMETIMES        = "sometimes"
#     RARELY           = "rarely"
#     NOT_REPRODUCIBLE = "not_reproducible"


# class PriorityLevelEnum(str, enum.Enum):
#     """
#     Computed output of the priority scoring engine.
#     high ≥ 70 | medium ≥ 40 | low < 40
#     """
#     HIGH   = "high"
#     MEDIUM = "medium"
#     LOW    = "low"


# class StatusEnum(str, enum.Enum):
#     """
#     Workflow FSM states (Section 6.5).
#     Legal transitions:
#         new → assigned → in_progress → resolved
#     No backward transitions. No skipping states.
#     """
#     NEW         = "new"
#     ASSIGNED    = "assigned"
#     IN_PROGRESS = "in_progress"
#     RESOLVED    = "resolved"


# # ============================================================
# # Bug Model
# # ============================================================

# class Bug(BaseModel):
#     """
#     Represents a single bug report submitted through the system.

#     Relationships:
#         assignee        : User who is assigned this bug
#         history         : All audit log entries for this bug
#         fix_suggestions : Fix records whose source_bug_id = this bug
#     """

#     __tablename__ = "bugs"

#     # ----------------------------------------------------------
#     # Report Fields (paper Section 6.1)
#     # ----------------------------------------------------------
#     title: Mapped[str] = mapped_column(
#         String(255),
#         nullable=False,
#         comment="Short descriptive title of the bug",
#     )

#     description: Mapped[str] = mapped_column(
#         Text,
#         nullable=False,
#         comment="Full description: what happened, steps to reproduce, expected vs actual",
#     )

#     module: Mapped[str] = mapped_column(
#         String(100),
#         nullable=False,
#         index=True,
#         comment="Affected software module or component",
#     )

#     location: Mapped[str] = mapped_column(
#         String(255),
#         nullable=False,
#         comment="File path, URL, or screen name where the bug occurs",
#     )

#     # ----------------------------------------------------------
#     # Bug Classification
#     # ----------------------------------------------------------
#     bug_type: Mapped[BugTypeEnum] = mapped_column(
#         SAEnum(BugTypeEnum, name="bug_type_enum", create_type=False),
#         nullable=False,
#         default=BugTypeEnum.UNKNOWN,
#         index=True,
#         comment="Bug type provided by the reporter",
#     )

#     category: Mapped[CategoryEnum] = mapped_column(
#         SAEnum(CategoryEnum, name="category_enum", create_type=False),
#         nullable=False,
#         default=CategoryEnum.UNCATEGORIZED,
#         index=True,
#         comment="Category assigned by the rule-based classification engine",
#     )

#     # ----------------------------------------------------------
#     # Scoring Inputs (paper Section 6.3)
#     # ----------------------------------------------------------
#     severity: Mapped[SeverityEnum] = mapped_column(
#         SAEnum(SeverityEnum, name="severity_enum", create_type=False),
#         nullable=False,
#         default=SeverityEnum.MEDIUM,
#         index=True,
#         comment="Severity level as assessed by the reporter",
#     )

#     frequency: Mapped[FrequencyEnum] = mapped_column(
#         SAEnum(FrequencyEnum, name="frequency_enum", create_type=False),
#         nullable=False,
#         default=FrequencyEnum.OCCASIONAL,
#         comment="How often the bug manifests",
#     )

#     impact: Mapped[ImpactEnum] = mapped_column(
#         SAEnum(ImpactEnum, name="impact_enum", create_type=False),
#         nullable=False,
#         default=ImpactEnum.MEDIUM,
#         comment="Business or user-experience impact level",
#     )

#     reproducibility: Mapped[ReproducibilityEnum] = mapped_column(
#         SAEnum(ReproducibilityEnum, name="reproducibility_enum", create_type=False),
#         nullable=False,
#         default=ReproducibilityEnum.SOMETIMES,
#         comment="Whether the bug can be reliably reproduced",
#     )

#     environment: Mapped[str] = mapped_column(
#         String(255),
#         nullable=False,
#         default="production",
#         comment="Environment where the bug was observed (production/staging/dev)",
#     )

#     # ----------------------------------------------------------
#     # Computed Priority (output of priority engine)
#     # ----------------------------------------------------------
#     priority_score: Mapped[float] = mapped_column(
#         Numeric(5, 2),
#         nullable=False,
#         default=0.00,
#         comment="Raw numeric score from the weighted priority formula",
#     )

#     priority_level: Mapped[PriorityLevelEnum] = mapped_column(
#         SAEnum(PriorityLevelEnum, name="priority_level_enum", create_type=False),
#         nullable=False,
#         default=PriorityLevelEnum.LOW,
#         index=True,
#         comment="Bucketed priority: high / medium / low",
#     )

#     # ----------------------------------------------------------
#     # Workflow State Machine (paper Section 6.5)
#     # ----------------------------------------------------------
#     status: Mapped[StatusEnum] = mapped_column(
#         SAEnum(StatusEnum, name="status_enum", create_type=False),
#         nullable=False,
#         default=StatusEnum.NEW,
#         index=True,
#         comment="Current FSM state: new → assigned → in_progress → resolved",
#     )

#     # ----------------------------------------------------------
#     # Assignment
#     # ----------------------------------------------------------
#     assigned_to: Mapped[Optional[str]] = mapped_column(
#         String(36),
#         ForeignKey("users.id", ondelete="SET NULL", onupdate="CASCADE"),
#         nullable=True,
#         default=None,
#         index=True,
#         comment="FK → users.id — developer currently responsible for this bug",
#     )

#     # ----------------------------------------------------------
#     # Soft Delete + Resolved Timestamp
#     # Bugs are never hard-deleted (paper Section 8.6).
#     # ----------------------------------------------------------
#     is_deleted: Mapped[bool] = mapped_column(
#         Boolean,
#         nullable=False,
#         default=False,
#         index=True,
#         comment="Soft delete flag — bugs are never physically removed",
#     )

#     resolved_at: Mapped[Optional[datetime]] = mapped_column(
#         DateTime,
#         nullable=True,
#         default=None,
#         comment="Timestamp when the bug reached Resolved status",
#     )

#     # ----------------------------------------------------------
#     # Relationships
#     # ----------------------------------------------------------
#     assignee: Mapped[Optional["User"]] = relationship(          # noqa: F821
#         "User",
#         back_populates="bugs_assigned",
#         foreign_keys=[assigned_to],
#         lazy="joined",      # always load assignee in the same query
#     )

#     history: Mapped[list["BugHistory"]] = relationship(         # noqa: F821
#         "BugHistory",
#         back_populates="bug",
#         foreign_keys="BugHistory.bug_id",
#         cascade="all, delete-orphan",
#         order_by="BugHistory.created_at",
#         lazy="select",
#     )

#     fix_suggestions: Mapped[list["FixSuggestion"]] = relationship(  # noqa: F821
#         "FixSuggestion",
#         back_populates="source_bug",
#         foreign_keys="FixSuggestion.source_bug_id",
#         lazy="select",
#     )

#     # ----------------------------------------------------------
#     # Table-level composite indexes
#     # ----------------------------------------------------------
#     __table_args__ = (
#         # Used by fix suggestion lookup (Section 6.4)
#         Index("idx_bugs_type_module_cat", "bug_type", "module", "category"),
#         # Common list/filter queries
#         Index("idx_bugs_status_priority", "status", "priority_level"),
#         Index("idx_bugs_module_status",   "module",  "status"),
#         {"comment": "Core bug report entity"},
#     )

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    Boolean,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base_model import BaseModel


class Bug(BaseModel):
    __tablename__ = "bugs"

    # Basic Info
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    module: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    location: Mapped[str] = mapped_column(String(255), nullable=False)

    # Classification
    bug_type: Mapped[str] = mapped_column(String(50), default="unknown")
    category: Mapped[str] = mapped_column(String(50), default="uncategorized")

    # Scoring
    severity: Mapped[str] = mapped_column(String(20), default="medium")
    frequency: Mapped[str] = mapped_column(String(20), default="occasional")
    impact: Mapped[str] = mapped_column(String(20), default="medium")
    reproducibility: Mapped[str] = mapped_column(String(20), default="sometimes")

    environment: Mapped[str] = mapped_column(String(255), default="production")

    # Priority
    priority_score: Mapped[float] = mapped_column(Numeric(5, 2), default=0.0)
    priority_level: Mapped[str] = mapped_column(String(20), default="low", index=True)

    # Workflow
    status: Mapped[str] = mapped_column(String(20), default="new", index=True)

    # Assignment
    assigned_to: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Soft delete
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    assignee = relationship("User", back_populates="bugs_assigned")

    history = relationship(
        "BugHistory",
        back_populates="bug",
        cascade="all, delete-orphan",
    )

    fix_suggestions = relationship(
        "FixSuggestion",
        back_populates="source_bug",
    )

    __table_args__ = (
        Index("idx_bugs_module_status", "module", "status"),
    )