# ============================================================
# database.py
# Sets up the SQLAlchemy engine, session factory, and
# declarative base that all ORM models inherit from.
# ============================================================

import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import QueuePool

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# ============================================================
# Engine
# Creates a single engine instance (connection pool) shared
# across the entire application lifetime.
# ============================================================
engine = create_engine(
    settings.DATABASE_URL,

    # Connection pool configuration
    poolclass=QueuePool,
    pool_size=settings.DB_POOL_SIZE,            # persistent connections kept open
    max_overflow=settings.DB_MAX_OVERFLOW,      # extra connections allowed under load
    pool_timeout=settings.DB_POOL_TIMEOUT,      # seconds to wait for a free connection
    pool_recycle=settings.DB_POOL_RECYCLE,      # recycle stale connections (MySQL drops
                                                # idle connections after wait_timeout)
    pool_pre_ping=True,                         # test connection health before using it
                                                # prevents "MySQL server has gone away"

    # Logging
    echo=settings.DB_ECHO,                      # logs all SQL if True (dev only)

    # MySQL/PyMySQL specific
    connect_args={
        "connect_timeout": 10,                  # fail fast if DB is unreachable
        "charset": "utf8mb4",
    },
)


# ============================================================
# Session Factory
# Each request gets its own Session (unit of work).
# autocommit=False means we control transactions explicitly.
# autoflush=False means we flush manually before queries.
# ============================================================
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,     # keep objects usable after session.commit()
)


# ============================================================
# Declarative Base
# All ORM models inherit from this Base.
# It holds the MetaData registry used by create_all / drop_all.
# ============================================================
class Base(DeclarativeBase):
    """
    Project-wide SQLAlchemy declarative base.
    Importing this in every model file and then calling
    Base.metadata.create_all(engine) will create every table
    whose model has been imported.
    """
    pass


# ============================================================
# MySQL utf8mb4 enforcement
# Fires after every new connection is established.
# Ensures the session character set matches the schema.
# ============================================================
@event.listens_for(engine, "connect")
def set_mysql_charset(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("SET NAMES utf8mb4")
    cursor.execute("SET CHARACTER SET utf8mb4")
    cursor.execute("SET character_set_connection=utf8mb4")
    cursor.close()


# ============================================================
# FastAPI Dependency — get_db
# Yields a database session per HTTP request.
# The finally block guarantees the session is always closed,
# even if an exception is raised inside the route handler.
#
# Usage in a route:
#   from app.database import get_db
#   def my_route(db: Session = Depends(get_db)): ...
# ============================================================
def get_db() -> Generator[Session, None, None]:
    db: Session = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ============================================================
# Context Manager — db_session
# For use outside FastAPI request scope (scripts, tests,
# background tasks, seeding).
#
# Usage:
#   with db_session() as db:
#       db.add(some_object)
# ============================================================
@contextmanager
def db_session() -> Generator[Session, None, None]:
    db: Session = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ============================================================
# Health check utility
# Called at startup to verify the DB is reachable.
# ============================================================
def check_database_connection() -> bool:
    """
    Attempts a lightweight SELECT 1 query.
    Returns True if the database is reachable, False otherwise.
    Logs the outcome either way.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection verified successfully.")
        return True
    except Exception as exc:
        logger.error("Database connection FAILED: %s", exc)
        return False


# ============================================================
# Table creation utility
# Only used in development / testing.
# In production, run schema.sql directly via migrations.
# ============================================================
def create_tables() -> None:
    """
    Creates all tables whose models have been imported into
    the models package. Safe to call multiple times
    (uses CREATE TABLE IF NOT EXISTS under the hood).
    """
    # Import all models so their metadata is registered on Base
    from app.models import bug, bug_history, fix_suggestion, user  # noqa: F401

    Base.metadata.create_all(bind=engine)
    logger.info("All database tables created (or already exist).")