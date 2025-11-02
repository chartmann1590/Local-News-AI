from __future__ import annotations

import os
import logging
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, declarative_base

logger = logging.getLogger(__name__)

DB_PATH = os.environ.get("DB_PATH", "/data/app.db")
DB_URL = f"sqlite:///{DB_PATH}"

# SQLite configuration for better reliability:
# - WAL mode for better concurrency and crash recovery
# - Pool size and timeout for connection management
# - Retry on I/O errors
engine = create_engine(
    DB_URL,
    connect_args={
        "check_same_thread": False,
        "timeout": 30.0,  # 30 second timeout for operations
    },
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,  # Verify connections before using them
    pool_recycle=3600,  # Recycle connections after 1 hour
)

# Enable WAL mode for better concurrency and reliability
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Set SQLite pragmas for better reliability."""
    try:
        cursor = dbapi_conn.cursor()
        # Enable WAL mode for better concurrency
        cursor.execute("PRAGMA journal_mode=WAL")
        # Set synchronous mode to NORMAL (safer than OFF, faster than FULL)
        cursor.execute("PRAGMA synchronous=NORMAL")
        # Increase busy timeout
        cursor.execute("PRAGMA busy_timeout=30000")
        # Enable foreign keys
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    except Exception as e:
        logger.warning(f"Failed to set SQLite pragmas: {e}")

# Keep attributes available after commit so detached objects can be used safely
# across background tasks without triggering refreshes on closed sessions.
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)
Base = declarative_base()


def init_db():
    from . import models  # noqa: F401 - ensure models are imported
    try:
        Base.metadata.create_all(bind=engine)
        # Migration: Add wind_speed_unit column if it doesn't exist
        with engine.connect() as conn:
            # Check if column exists by inspecting table info
            result = conn.execute(text("PRAGMA table_info(app_settings)"))
            columns = [row[1] for row in result]
            if "wind_speed_unit" not in columns:
                conn.execute(text("ALTER TABLE app_settings ADD COLUMN wind_speed_unit VARCHAR(10)"))
                conn.commit()
    except Exception as e:
        logger.error(f"Database initialization failed: {e}", exc_info=True)
        raise
