# # ============================================================
# # models/bug_history.py
# # Permanent, append-only audit trail of every state change.
# # Paper Section 8.6: "bugs can never be erased — history is
# # permanent. A developer can always track actions and attribute
# # them to a specific user."
# # ============================================================

# import enum
# from typing import Optional

# from sqlalchemy import Enum as SAEnum, ForeignKey, Index, String, Text
# from sqlalchemy.orm import Mapped, mapped_column, relationship

# from app.models.base_model import BaseModel, TimestampMixin
# from sqlalchemy import DateTime
# from sqlalchemy.orm import DeclarativeBase
# from app.database import Base


# class ChangeSourceEnum(str, enum.Enum):
#     """
#     Who or what triggered this history record.
#     USER   — a developer performed the action manually via the API.
#     SYSTEM — the rule engine or workflow engine triggered the change.
#     """
#     USER   = "user"
#     SYSTEM = "system"


# class BugHistory(Base, TimestampMixin):
#     """
#     One row is written for every meaningful change to a Bug row.

#     Tracked events (field_changed values):
#         - status          : FSM state transition
#         - assigned_to     : assignment changed
#         - priority_level  : priority recalculated
#         - priority_score  : score value changed
#         - category        : classification engine re-categorised
#         - created         : initial row creation event

#     Relationships:
#         bug             : the Bug this record belongs to
#         changed_by_user : the User who triggered the change (nullable)
#     """

#     __tablename__ = "bug_history"

#     # ----------------------------------------------------------
#     # Primary key — UUID, same pattern as BaseModel
#     # (BugHistory intentionally does NOT inherit BaseModel because
#     #  it has no updated_at column — history rows are immutable)
#     # ----------------------------------------------------------
#     import uuid
#     id: Mapped[str] = mapped_column(
#         String(36),
#         primary_key=True,
#         default=lambda: str(__import__("uuid").uuid4()),
#         comment="UUID primary key",
#     )

#     # ----------------------------------------------------------
#     # Foreign key → bugs
#     # ON DELETE RESTRICT: history must outlive the bug record
#     # (soft-delete the bug instead of hard deleting it)
#     # ----------------------------------------------------------
#     bug_id: Mapped[str] = mapped_column(
#         String(36),
#         ForeignKey("bugs.id", ondelete="RESTRICT", onupdate="CASCADE"),
#         nullable=False,
#         index=True,
#         comment="FK → bugs.id",
#     )

#     # ----------------------------------------------------------
#     # What changed
#     # ----------------------------------------------------------
#     field_changed: Mapped[str] = mapped_column(
#         String(100),
#         nullable=False,
#         index=True,
#         comment="Name of the field that was changed (e.g. status, assigned_to)",
#     )

#     old_value: Mapped[Optional[str]] = mapped_column(
#         String(255),
#         nullable=True,
#         default=None,
#         comment="Value before the change (NULL for creation events)",
#     )

#     new_value: Mapped[Optional[str]] = mapped_column(
#         String(255),
#         nullable=True,
#         default=None,
#         comment="Value after the change",
#     )

#     # ----------------------------------------------------------
#     # Who / what caused the change
#     # ----------------------------------------------------------
#     changed_by: Mapped[Optional[str]] = mapped_column(
#         String(36),
#         ForeignKey("users.id", ondelete="SET NULL", onupdate="CASCADE"),
#         nullable=True,
#         default=None,
#         index=True,
#         comment="FK → users.id — NULL means the system triggered the change",
#     )

#     change_source: Mapped[ChangeSourceEnum] = mapped_column(
#         SAEnum(ChangeSourceEnum, name="change_source_enum", create_type=False),
#         nullable=False,
#         default=ChangeSourceEnum.SYSTEM,
#         comment="Whether the change was triggered by a user or the rule engine",
#     )

#     notes: Mapped[Optional[str]] = mapped_column(
#         Text,
#         nullable=True,
#         default=None,
#         comment="Optional human-readable note explaining the change",
#     )

#     # ----------------------------------------------------------
#     # Relationships
#     # ----------------------------------------------------------
#     bug: Mapped["Bug"] = relationship(                          # noqa: F821
#         "Bug",
#         back_populates="history",
#         foreign_keys=[bug_id],
#         lazy="select",
#     )

#     changed_by_user: Mapped[Optional["User"]] = relationship(  # noqa: F821
#         "User",
#         back_populates="history_entries",
#         foreign_keys=[changed_by],
#         lazy="joined",
#     )

#     # ----------------------------------------------------------
#     # Table-level indexes
#     # ----------------------------------------------------------
#     __table_args__ = (
#         Index("idx_history_bug_id",         "bug_id"),
#         Index("idx_history_field_changed",  "field_changed"),
#         Index("idx_history_bug_field",      "bug_id", "field_changed"),
#         {"comment": "Immutable audit trail — one row per bug field change"},
#     )

# models/bug_history.py

from typing import Optional

from sqlalchemy import ForeignKey, String, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base_model import BaseModel


class BugHistory(BaseModel):
    __tablename__ = "bug_history"

    # ─────────────────────────────────────────────
    # Foreign key → bugs
    # ─────────────────────────────────────────────
    bug_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("bugs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # ─────────────────────────────────────────────
    # Change tracking
    # ─────────────────────────────────────────────
    field_changed: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    old_value: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    new_value: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # ─────────────────────────────────────────────
    # Actor
    # ─────────────────────────────────────────────
    changed_by: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    change_source: Mapped[str] = mapped_column(
        String(20),
        default="system",
    )

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ─────────────────────────────────────────────
    # Relationships
    # ─────────────────────────────────────────────
    bug: Mapped["Bug"] = relationship("Bug", back_populates="history")

    changed_by_user: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="history_entries"
    )

    # ─────────────────────────────────────────────
    # Indexes
    # ─────────────────────────────────────────────
    __table_args__ = (
        Index("idx_history_bug_id", "bug_id"),
        Index("idx_history_field", "field_changed"),
        Index("idx_history_bug_field", "bug_id", "field_changed"),
    )