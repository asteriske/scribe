"""Database migration utilities."""
import logging
from sqlalchemy import text, inspect

logger = logging.getLogger(__name__)


def add_tags_column_if_missing(engine):
    """Add tags column to transcriptions table if it doesn't exist."""
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns('transcriptions')]

    if 'tags' not in columns:
        logger.info("Adding tags column to transcriptions table")
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE transcriptions ADD COLUMN tags TEXT DEFAULT '[]'"))
            conn.commit()
        logger.info("Tags column added successfully")
    else:
        logger.debug("Tags column already exists")


def create_summaries_table_if_missing(engine):
    """Create summaries table if it doesn't exist."""
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    if 'summaries' not in tables:
        logger.info("Creating summaries table")
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE summaries (
                    id TEXT PRIMARY KEY,
                    transcription_id TEXT NOT NULL,
                    api_endpoint TEXT NOT NULL,
                    model TEXT NOT NULL,
                    api_key_used INTEGER DEFAULT 0,
                    system_prompt TEXT NOT NULL,
                    tags_at_time TEXT NOT NULL DEFAULT '[]',
                    config_source TEXT,
                    summary_text TEXT NOT NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    generation_time_ms INTEGER,
                    prompt_tokens INTEGER,
                    completion_tokens INTEGER,
                    FOREIGN KEY (transcription_id) REFERENCES transcriptions (id)
                )
            """))
            # Create indexes
            conn.execute(text(
                "CREATE INDEX idx_summary_transcription_id ON summaries (transcription_id)"
            ))
            conn.execute(text(
                "CREATE INDEX idx_summary_created_at ON summaries (created_at DESC)"
            ))
            conn.commit()
        logger.info("Summaries table created successfully")
    else:
        logger.debug("Summaries table already exists")


def add_source_context_column_if_missing(engine):
    """Add source_context column to transcriptions table if it doesn't exist."""
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns('transcriptions')]

    if 'source_context' not in columns:
        logger.info("Adding source_context column to transcriptions table")
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE transcriptions ADD COLUMN source_context TEXT"))
            conn.commit()
        logger.info("source_context column added successfully")
    else:
        logger.debug("source_context column already exists")


def run_migrations(engine):
    """Run all pending migrations."""
    logger.info("Running database migrations")
    add_tags_column_if_missing(engine)
    create_summaries_table_if_missing(engine)
    add_source_context_column_if_missing(engine)
    logger.info("Migrations complete")
