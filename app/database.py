from __future__ import annotations

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base


DB_PATH = os.environ.get("DB_PATH", "/data/app.db")
DB_URL = f"sqlite:///{DB_PATH}"

# SQLite needs check_same_thread=False for multithreaded FastAPI + APScheduler
engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
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
    Base.metadata.create_all(bind=engine)
