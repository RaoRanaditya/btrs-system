from typing import Optional
from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base_model import BaseModel

class BugHistory(BaseModel):
    __tablename__ = "bug_history"
    bug_id: Mapped[str] = mapped_column(String(36), ForeignKey("bugs.id", ondelete="RESTRICT"), nullable=False, index=True)
    field_changed: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    old_value: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    new_value: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    changed_by: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    change_source: Mapped[str] = mapped_column(String(20), default="system")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    bug = relationship("Bug", back_populates="history")
    changed_by_user = relationship("User", back_populates="history_entries", foreign_keys=[changed_by])
    __table_args__ = (
        Index("idx_history_bug_id", "bug_id"),
        Index("idx_history_field", "field_changed"),
        Index("idx_history_bug_field", "bug_id", "field_changed"),
    )
