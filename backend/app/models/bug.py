from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base_model import BaseModel


class Bug(BaseModel):
    __tablename__ = "bugs"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    module: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    location: Mapped[str] = mapped_column(String(255), nullable=False, default="")

    bug_type: Mapped[str] = mapped_column(String(50), default="unknown")
    category: Mapped[str] = mapped_column(String(50), default="uncategorized")

    severity: Mapped[str] = mapped_column(String(20), default="medium")
    frequency: Mapped[int] = mapped_column(default=1)
    impact: Mapped[int] = mapped_column(default=1)
    reproducibility: Mapped[int] = mapped_column(default=1)

    environment: Mapped[str] = mapped_column(String(255), default="production")

    priority_score: Mapped[float] = mapped_column(Numeric(5, 2), default=0.0)
    priority: Mapped[str] = mapped_column(String(20), default="Low", index=True)

    status: Mapped[str] = mapped_column(String(20), default="New", index=True)

    assigned_to: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    reported_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    assignee = relationship("User", back_populates="bugs_assigned", foreign_keys=[assigned_to])
    history = relationship("BugHistory", back_populates="bug", cascade="all, delete-orphan")
    fix_suggestions = relationship("FixSuggestion", back_populates="source_bug")

    __table_args__ = (
        Index("idx_bugs_module_status", "module", "status"),
    )