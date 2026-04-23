# # ============================================================
# # models/fix_suggestion.py
# # Historical fix knowledge base.
# # Paper Section 6.4: "The system uses stored information to
# # resolve new problems by looking at past solutions.
# # The category, software section, and type of error retrieve
# # the memories of previous documents."
# # ============================================================

# from typing import Optional

# from sqlalchemy import (
#     Boolean,
#     Enum as SAEnum,
#     ForeignKey,
#     Index,
#     Integer,
#     Numeric,
#     String,
#     Text,
# )
# from sqlalchemy.orm import Mapped, mapped_column, relationship

# from app.models.base_model import BaseModel
# from app.models.bug import BugTypeEnum, CategoryEnum


# class FixSuggestion(BaseModel):
#     """
#     One row = one documented resolution for a class of bugs.

#     The suggestion engine (Section 6.4) queries this table using
#     a three-dimension match: bug_type + module + category.

#     When a bug is resolved, a new row is inserted here so the
#     knowledge base grows automatically over time.

#     Ranking:
#         When multiple fixes match, results are ordered by:
#         1. times_applied DESC   (most-used fix first)
#         2. confidence_score DESC (manually curated quality score)

#     Relationships:
#         source_bug : the Bug whose resolution generated this fix
#     """

#     __tablename__ = "fix_suggestions"

#     # ----------------------------------------------------------
#     # Source traceability
#     # ----------------------------------------------------------
#     source_bug_id: Mapped[Optional[str]] = mapped_column(
#         String(36),
#         ForeignKey("bugs.id", ondelete="SET NULL", onupdate="CASCADE"),
#         nullable=True,
#         default=None,
#         index=True,
#         comment="FK → bugs.id — the resolved bug that produced this fix (NULL for seed data)",
#     )

#     # ----------------------------------------------------------
#     # Three matching dimensions (Section 6.4)
#     # Used in the WHERE clause of the suggestion lookup query.
#     # ----------------------------------------------------------
#     bug_type: Mapped[BugTypeEnum] = mapped_column(
#         SAEnum(BugTypeEnum, name="bug_type_enum", create_type=False),
#         nullable=False,
#         comment="Bug type dimension for matching",
#     )

#     module: Mapped[str] = mapped_column(
#         String(100),
#         nullable=False,
#         index=True,
#         comment="Module/component dimension for matching",
#     )

#     category: Mapped[CategoryEnum] = mapped_column(
#         SAEnum(CategoryEnum, name="category_enum", create_type=False),
#         nullable=False,
#         comment="Category dimension for matching",
#     )

#     # ----------------------------------------------------------
#     # Fix content
#     # ----------------------------------------------------------
#     problem_summary: Mapped[str] = mapped_column(
#         String(500),
#         nullable=False,
#         comment="Short description of the original problem this fix addresses",
#     )

#     fix_description: Mapped[str] = mapped_column(
#         Text,
#         nullable=False,
#         comment="Step-by-step resolution instructions",
#     )

#     fix_tags: Mapped[Optional[str]] = mapped_column(
#         String(500),
#         nullable=True,
#         default=None,
#         comment="Comma-separated keywords for boosting relevance in partial matches",
#     )

#     # ----------------------------------------------------------
#     # Relevance tracking
#     # ----------------------------------------------------------
#     times_applied: Mapped[int] = mapped_column(
#         Integer,
#         nullable=False,
#         default=0,
#         comment="How many times this fix has been returned as a suggestion",
#     )

#     confidence_score: Mapped[float] = mapped_column(
#         Numeric(3, 2),
#         nullable=False,
#         default=1.00,
#         comment="Manual quality rating 0.00–1.00 (higher = more reliable fix)",
#     )

#     is_active: Mapped[bool] = mapped_column(
#         Boolean,
#         nullable=False,
#         default=True,
#         index=True,
#         comment="Soft disable stale or incorrect fixes without deleting them",
#     )

#     # ----------------------------------------------------------
#     # Relationships
#     # ----------------------------------------------------------
#     source_bug: Mapped[Optional["Bug"]] = relationship(     # noqa: F821
#         "Bug",
#         back_populates="fix_suggestions",
#         foreign_keys=[source_bug_id],
#         lazy="select",
#     )

#     # ----------------------------------------------------------
#     # Table-level composite indexes
#     # ----------------------------------------------------------
#     __table_args__ = (
#         # Primary lookup index — covers the 3-dimension WHERE clause
#         Index("idx_fix_type_module_cat",  "bug_type", "module", "category"),
#         # Partial-match fallbacks
#         Index("idx_fix_module_cat",       "module",   "category"),
#         Index("idx_fix_type_cat",         "bug_type", "category"),
#         # Sorting index
#         Index("idx_fix_times_applied",    "times_applied"),
#         Index("idx_fix_confidence",       "confidence_score"),
#         {"comment": "Historical fix knowledge base — grows as bugs are resolved"},
#     )

#     def tag_list(self) -> list[str]:
#         """Returns fix_tags as a Python list, or [] if none set."""
#         if not self.fix_tags:
#             return []
#         return [tag.strip() for tag in self.fix_tags.split(",") if tag.strip()]

# models/fix_suggestion.py

from typing import Optional

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base_model import BaseModel


class FixSuggestion(BaseModel):
    __tablename__ = "fix_suggestions"

    # Source bug
    source_bug_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("bugs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Matching dimensions
    bug_type: Mapped[str] = mapped_column(String(50), nullable=False)
    module: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)

    # Fix content
    problem_summary: Mapped[str] = mapped_column(String(500), nullable=False)
    fix_description: Mapped[str] = mapped_column(Text, nullable=False)

    fix_tags: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Tracking
    times_applied: Mapped[int] = mapped_column(Integer, default=0)
    confidence_score: Mapped[float] = mapped_column(Numeric(3, 2), default=1.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    # Relationships
    source_bug = relationship("Bug", back_populates="fix_suggestions")

    # Indexes
    __table_args__ = (
        Index("idx_fix_type_module_cat", "bug_type", "module", "category"),
        Index("idx_fix_module_cat", "module", "category"),
    )

    def tag_list(self) -> list[str]:
        if not self.fix_tags:
            return []
        return [tag.strip() for tag in self.fix_tags.split(",") if tag.strip()]