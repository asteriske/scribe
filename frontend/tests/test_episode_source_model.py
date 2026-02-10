"""Tests for EpisodeSource model and migration."""
import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from frontend.core.database import init_db
from frontend.core.models import Base, Transcription, EpisodeSource
from frontend.core.migrations import create_episode_sources_table_if_missing


@pytest.fixture
def engine():
    """Create in-memory test database."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    init_db(engine)
    return engine


@pytest.fixture
def session(engine):
    """Create a database session."""
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


class TestEpisodeSourceModel:
    """Tests for the EpisodeSource SQLAlchemy model."""

    def test_create_episode_source(self, session):
        """Test creating an episode source linked to a transcription."""
        transcription = Transcription(
            id="test_123",
            source_type="apple_podcasts",
            source_url="https://podcasts.apple.com/test",
            status="completed",
        )
        session.add(transcription)
        session.commit()

        es = EpisodeSource(
            id="es_abc123",
            transcription_id="test_123",
            email_subject="New episode: Test Podcast",
            email_from="newsletter@example.com",
            source_text="This week we discuss testing.",
            matched_url="https://podcasts.apple.com/test",
        )
        session.add(es)
        session.commit()

        result = session.query(EpisodeSource).filter_by(id="es_abc123").first()
        assert result is not None
        assert result.transcription_id == "test_123"
        assert result.email_subject == "New episode: Test Podcast"
        assert result.source_text == "This week we discuss testing."
        assert result.matched_url == "https://podcasts.apple.com/test"
        assert result.created_at is not None

    def test_to_dict(self, session):
        """Test to_dict serialization."""
        transcription = Transcription(
            id="test_456",
            source_type="youtube",
            source_url="https://youtube.com/watch?v=test",
            status="completed",
        )
        session.add(transcription)
        session.commit()

        es = EpisodeSource(
            id="es_def456",
            transcription_id="test_456",
            email_subject="Check this out",
            email_from="user@example.com",
            source_text="Great episode about Python.",
            matched_url="https://youtube.com/watch?v=test",
        )
        session.add(es)
        session.commit()

        d = es.to_dict()
        assert d["id"] == "es_def456"
        assert d["transcription_id"] == "test_456"
        assert d["email_subject"] == "Check this out"
        assert d["email_from"] == "user@example.com"
        assert d["source_text"] == "Great episode about Python."
        assert d["matched_url"] == "https://youtube.com/watch?v=test"
        assert "created_at" in d

    def test_cascade_delete(self, session):
        """Test that deleting a transcription deletes linked episode sources."""
        transcription = Transcription(
            id="test_789",
            source_type="apple_podcasts",
            source_url="https://podcasts.apple.com/cascade",
            status="completed",
        )
        session.add(transcription)
        session.commit()

        es = EpisodeSource(
            id="es_ghi789",
            transcription_id="test_789",
            source_text="Will be deleted.",
            matched_url="https://podcasts.apple.com/cascade",
        )
        session.add(es)
        session.commit()

        session.delete(transcription)
        session.commit()

        result = session.query(EpisodeSource).filter_by(id="es_ghi789").first()
        assert result is None

    def test_relationship_from_transcription(self, session):
        """Test accessing episode_sources from a transcription."""
        transcription = Transcription(
            id="test_rel",
            source_type="youtube",
            source_url="https://youtube.com/watch?v=rel",
            status="completed",
        )
        session.add(transcription)
        session.commit()

        es = EpisodeSource(
            id="es_rel",
            transcription_id="test_rel",
            source_text="Relationship test.",
            matched_url="https://youtube.com/watch?v=rel",
        )
        session.add(es)
        session.commit()

        session.refresh(transcription)
        assert len(transcription.episode_sources) == 1
        assert transcription.episode_sources[0].id == "es_rel"


class TestEpisodeSourceMigration:
    """Tests for the episode_sources migration."""

    def test_migration_creates_table(self):
        """Test that migration creates episode_sources table."""
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.tables["transcriptions"].create(engine)

        inspector = inspect(engine)
        assert "episode_sources" not in inspector.get_table_names()

        create_episode_sources_table_if_missing(engine)

        inspector = inspect(engine)
        assert "episode_sources" in inspector.get_table_names()

    def test_migration_is_idempotent(self):
        """Test that running migration twice doesn't error."""
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.tables["transcriptions"].create(engine)

        create_episode_sources_table_if_missing(engine)
        create_episode_sources_table_if_missing(engine)  # Should not raise
