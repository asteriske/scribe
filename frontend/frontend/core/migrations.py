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


def run_migrations(engine):
    """Run all pending migrations."""
    logger.info("Running database migrations")
    add_tags_column_if_missing(engine)
    logger.info("Migrations complete")
