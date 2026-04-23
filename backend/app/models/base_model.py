# ============================================================
# models/base_model.py
# Abstract mixin that every ORM model inherits.
# Provides: UUID primary key, created_at, updated_at.
# Keeps individual model files clean and DRY.
# ============================================================

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TimestampMixin:
    """
    Adds created_at and updated_at columns to any model.

    - created_at is set once by the DB server on INSERT.
    - updated_at is automatically refreshed by the DB server
      on every UPDATE via ON UPDATE CURRENT_TIMESTAMP.
    - server_default / onupdate use DB-side functions so the
      values are always accurate even for bulk operations that
      bypass Python.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),          # DB sets value on INSERT
        comment="Row creation timestamp (UTC)",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),          # DB sets initial value on INSERT
        onupdate=func.now(),                # SQLAlchemy updates on ORM UPDATE
        comment="Last modification timestamp (UTC)",
    )


class UUIDPrimaryKeyMixin:
    """
    Adds a CHAR(36) UUID primary key column named `id`.

    UUIDs are generated in Python (not the DB) so:
    - The ID is known before the INSERT hits the database.
    - Works identically with MySQL 5.7, 8.0, and MariaDB.
    - No AUTO_INCREMENT race conditions in distributed setups.
    """

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),  # Python-side generation
        comment="UUID primary key (CHAR 36)",
    )


class BaseModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Abstract base class for all BTRS ORM models.

    Combines:
      - UUID primary key (UUIDPrimaryKeyMixin)
      - created_at / updated_at timestamps (TimestampMixin)
      - SQLAlchemy DeclarativeBase (Base)

    Usage:
        class Bug(BaseModel):
            __tablename__ = "bugs"
            title: Mapped[str] = mapped_column(String(255))
    """

    __abstract__ = True     # SQLAlchemy will NOT create a table for this class

    def to_dict(self) -> dict:
        """
        Utility: converts the model instance to a plain dict.
        Useful for logging and debugging.
        """
        return {
            col.name: getattr(self, col.name)
            for col in self.__table__.columns
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.id}>"