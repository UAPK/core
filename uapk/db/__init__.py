"""
Database module for OpsPilotOS
Handles database creation, sessions, and utilities.
"""
from pathlib import Path
from sqlmodel import SQLModel, create_engine, Session
from typing import Generator

# Global engine
_engine = None


def get_engine(db_path: str = "runtime/opspilotos.db"):
    """Get or create database engine"""
    global _engine
    if _engine is None:
        # Ensure directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # Create engine
        db_url = f"sqlite:///{db_path}"
        _engine = create_engine(db_url, echo=False, connect_args={"check_same_thread": False})

    return _engine


def init_db(db_path: str = "runtime/opspilotos.db"):
    """Initialize database: create all tables"""
    engine = get_engine(db_path)

    # Import all models to ensure they're registered
    from uapk.db import models  # noqa

    # Create all tables
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """Get database session (for dependency injection)"""
    engine = get_engine()
    with Session(engine) as session:
        yield session


def create_session() -> Session:
    """Create a new database session"""
    engine = get_engine()
    return Session(engine)
