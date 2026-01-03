"""Database initialization and session management."""

import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import Engine

from frontend.core.config import settings
from frontend.core.models import Base

logger = logging.getLogger(__name__)


def init_db(engine: Engine = None):
    """Initialize database schema and FTS5 tables."""
    if engine is None:
        engine = create_engine(
            settings.database_url,
            connect_args={"check_same_thread": False}  # SQLite specific
        )

    # Create tables
    Base.metadata.create_all(engine)

    # Create FTS5 virtual table
    with engine.connect() as conn:
        # Check if FTS table exists
        result = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='transcriptions_fts'"
        ))

        if not result.fetchone():
            logger.info("Creating FTS5 table and triggers")

            # Create FTS5 table
            conn.execute(text("""
                CREATE VIRTUAL TABLE transcriptions_fts USING fts5(
                    id UNINDEXED,
                    title,
                    channel,
                    content
                )
            """))

            # Insert trigger
            conn.execute(text("""
                CREATE TRIGGER transcriptions_ai AFTER INSERT ON transcriptions BEGIN
                    INSERT INTO transcriptions_fts(rowid, id, title, channel, content)
                    VALUES (new.rowid, new.id, new.title, new.channel, new.full_text);
                END
            """))

            # Update trigger
            conn.execute(text("""
                CREATE TRIGGER transcriptions_au AFTER UPDATE ON transcriptions BEGIN
                    UPDATE transcriptions_fts
                    SET title = new.title,
                        channel = new.channel,
                        content = new.full_text
                    WHERE rowid = new.rowid;
                END
            """))

            # Delete trigger
            conn.execute(text("""
                CREATE TRIGGER transcriptions_ad AFTER DELETE ON transcriptions BEGIN
                    DELETE FROM transcriptions_fts WHERE rowid = old.rowid;
                END
            """))

            conn.commit()

    logger.info("Database initialized successfully")
    return engine


def get_engine():
    """Get database engine."""
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False}
    )
    return engine


def get_session_maker():
    """Get session maker."""
    engine = get_engine()
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Get database session (dependency for FastAPI)."""
    SessionLocal = get_session_maker()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
