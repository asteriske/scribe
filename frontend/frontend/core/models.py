"""SQLAlchemy database models."""

from datetime import datetime, timedelta
from sqlalchemy import Column, String, Integer, DateTime, Text, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Transcription(Base):
    """Transcription job model."""

    __tablename__ = 'transcriptions'

    # Primary Key
    id = Column(String, primary_key=True)

    # Source Information
    source_type = Column(String, nullable=False)  # 'youtube', 'apple_podcasts', 'direct_audio'
    source_url = Column(String, nullable=False, unique=True)
    title = Column(String)
    channel = Column(String)
    thumbnail_url = Column(String)
    upload_date = Column(String)

    # Media Information
    duration_seconds = Column(Integer)
    file_size_bytes = Column(Integer)
    audio_format = Column(String)

    # File Paths
    audio_path = Column(String)
    transcription_path = Column(String)

    # Job Status
    status = Column(String, nullable=False, default='pending')
    progress = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    started_at = Column(DateTime)
    transcribed_at = Column(DateTime)
    audio_cached_until = Column(DateTime)

    # Transcription Metadata
    model_used = Column(String)
    language = Column(String)
    word_count = Column(Integer)
    segments_count = Column(Integer)

    # Error Handling
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)

    # Search
    full_text = Column(Text)

    def __repr__(self):
        return f"<Transcription {self.id} ({self.status})>"

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            'id': self.id,
            'source': {
                'type': self.source_type,
                'url': self.source_url,
                'title': self.title,
                'channel': self.channel,
                'thumbnail': self.thumbnail_url,
                'upload_date': self.upload_date
            },
            'status': self.status,
            'progress': self.progress,
            'duration_seconds': self.duration_seconds,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'transcribed_at': self.transcribed_at.isoformat() if self.transcribed_at else None,
            'model': self.model_used,
            'language': self.language,
            'word_count': self.word_count,
            'segments_count': self.segments_count,
            'error': self.error_message
        }


# Indexes
Index('idx_status', Transcription.status)
Index('idx_created_at', Transcription.created_at.desc())
Index('idx_transcribed_at', Transcription.transcribed_at.desc())
Index('idx_cached_until', Transcription.audio_cached_until)
Index('idx_source_type', Transcription.source_type)
