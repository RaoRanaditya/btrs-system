from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base_model import BaseModel


class FixSuggestion(BaseModel):
    __tablename__ = "fix_suggestions"

    source_bug_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("bugs.id", ondelete="SET NULL"), nullable=True, index=True
    )

    bug_type: Mapped[str] = mapped_column(String(50), nullable=False)
    module: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)

    problem_summary: Mapped[str] = mapped_column(String(500), nullable=False)
    fix_description: Mapped[str] = mapped_column(Text, nullable=False)
    fix_tags: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    times_applied: Mapped[int] = mapped_column(Integer, default=0)
    confidence_score: Mapped[float] = mapped_column(Numeric(3, 2), default=1.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    source_bug = relationship("Bug", back_populates="fix_suggestions")

    __table_args__ = (
        Index("idx_fix_type_module_cat", "bug_type", "module", "category"),
        Index("idx_fix_module_cat", "module", "category"),
    )

    def tag_list(self) -> list[str]:
        if not self.fix_tags:
            return []
        return [t.strip() for t in self.fix_tags.split(",") if t.strip()]