"""Test database models."""
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from frontend.core.models import Transcription
from frontend.core.database import init_db


@pytest.fixture
def test_db():
    """Create test database"""
    engine = create_engine("sqlite:///:memory:")
    init_db(engine)
    return engine


def test_transcription_model_creation(test_db):
    """Test creating a transcription record"""
    with Session(test_db) as session:
        transcription = Transcription(
            id="youtube_test123",
            source_type="youtube",
            source_url="https://youtube.com/watch?v=test123",
            title="Test Video",
            status="pending"
        )
        session.add(transcription)
        session.commit()

        # Query it back
        result = session.query(Transcription).filter_by(id="youtube_test123").first()
        assert result is not None
        assert result.title == "Test Video"
        assert result.status == "pending"
        assert result.progress == 0


def test_transcription_to_dict(test_db):
    """Test to_dict serialization"""
    with Session(test_db) as session:
        transcription = Transcription(
            id="youtube_test456",
            source_type="youtube",
            source_url="https://youtube.com/watch?v=test456",
            title="Test Video 2",
            status="completed",
            language="en",
            word_count=100
        )
        session.add(transcription)
        session.commit()

        data = transcription.to_dict()
        assert data["id"] == "youtube_test456"
        assert data["source"]["title"] == "Test Video 2"
        assert data["status"] == "completed"
        assert data["language"] == "en"


def test_fts5_search(test_db):
    """Test full-text search works"""
    with Session(test_db) as session:
        # Create some transcriptions
        t1 = Transcription(
            id="yt_1",
            source_type="youtube",
            source_url="https://youtube.com/watch?v=1",
            title="Python Tutorial",
            channel="Tech Channel",
            status="completed",
            full_text="This is a tutorial about Python programming language"
        )
        t2 = Transcription(
            id="yt_2",
            source_type="youtube",
            source_url="https://youtube.com/watch?v=2",
            title="JavaScript Guide",
            channel="Tech Channel",
            status="completed",
            full_text="Learn JavaScript from scratch"
        )
        session.add_all([t1, t2])
        session.commit()

        # Search for "Python"
        result = session.execute(text("""
            SELECT t.id, t.title
            FROM transcriptions t
            JOIN transcriptions_fts fts ON t.rowid = fts.rowid
            WHERE transcriptions_fts MATCH 'Python'
        """))
        rows = result.fetchall()

        assert len(rows) == 1
        assert rows[0][0] == "yt_1"
