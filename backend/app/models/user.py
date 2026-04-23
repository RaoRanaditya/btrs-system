# ============================================================
# models/user.py
# Represents a developer/team member who can be assigned bugs.
# ============================================================

from sqlalchemy import Boolean, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base_model import BaseModel


class User(BaseModel):
    """
    A user is any developer or team member in the system.

    Relationships:
        - bugs_assigned : list of Bug rows where assigned_to = this user
        - history_entries: list of BugHistory rows changed_by this user
    """

    __tablename__ = "users"

    # ----------------------------------------------------------
    # Columns
    # ----------------------------------------------------------
    username: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        comment="Unique login username",
    )

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        comment="Unique email address",
    )

    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Display name",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Soft disable without deleting the user",
    )

    # ----------------------------------------------------------
    # Relationships
    # back_populates must match the attribute name in Bug /
    # BugHistory that points back to User.
    # ----------------------------------------------------------
    bugs_assigned: Mapped[list["Bug"]] = relationship(           # noqa: F821
        "Bug",
        back_populates="assignee",
        foreign_keys="Bug.assigned_to",
        lazy="select",
    )

    history_entries: Mapped[list["BugHistory"]] = relationship(  # noqa: F821
        "BugHistory",
        back_populates="changed_by_user",
        foreign_keys="BugHistory.changed_by",
        lazy="select",
    )

    # ----------------------------------------------------------
    # Extra table-level indexes
    # ----------------------------------------------------------
    __table_args__ = (
        Index("idx_users_username", "username"),
        Index("idx_users_email", "email"),
        {"comment": "Developer/team member accounts"},
    )