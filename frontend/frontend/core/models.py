"""SQLAlchemy database models."""

from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, Index, Boolean, ForeignKey, func
from sqlalchemy.orm import declarative_base, relationship

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
    created_at = Column(DateTime, nullable=False, default=func.now())
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

    # Tags
    tags = Column(Text, nullable=False, default='[]')

    def __repr__(self):
        return f"<Transcription {self.id} ({self.status})>"

    def to_dict(self):
        """Convert to dictionary for API responses."""
        import json

        # Parse tags from JSON if it's a string
        tags_list = []
        if self.tags:
            if isinstance(self.tags, str):
                try:
                    tags_list = json.loads(self.tags)
                except (json.JSONDecodeError, TypeError):
                    tags_list = []
            elif isinstance(self.tags, list):
                tags_list = self.tags

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
            'error': self.error_message,
            'tags': tags_list
        }


class Summary(Base):
    """Summary model for storing AI-generated summaries of transcriptions."""

    __tablename__ = 'summaries'

    # Identity
    id = Column(String, primary_key=True)  # e.g., 'sum_abc123'
    transcription_id = Column(String, ForeignKey('transcriptions.id'), nullable=False)

    # Configuration used for this summary
    api_endpoint = Column(String, nullable=False)
    model = Column(String, nullable=False)
    api_key_used = Column(Boolean, default=False)  # Don't store the actual key
    system_prompt = Column(Text, nullable=False)
    tags_at_time = Column(Text, nullable=False, default='[]')  # JSON array
    config_source = Column(String)  # e.g., "tag:supersummarize" or "system_default"

    # Result
    summary_text = Column(Text, nullable=False)

    # Metadata
    created_at = Column(DateTime, nullable=False, default=func.now())
    generation_time_ms = Column(Integer)  # How long the API call took

    # Token usage (if API returns it)
    prompt_tokens = Column(Integer)
    completion_tokens = Column(Integer)

    # Relationship
    transcription = relationship("Transcription", backref="summaries")

    def __repr__(self):
        return f"<Summary {self.id} for {self.transcription_id}>"

    def to_dict(self):
        """Convert to dictionary for API responses."""
        import json

        # Parse tags from JSON if it's a string
        tags_list = []
        if self.tags_at_time:
            if isinstance(self.tags_at_time, str):
                try:
                    tags_list = json.loads(self.tags_at_time)
                except (json.JSONDecodeError, TypeError):
                    tags_list = []
            elif isinstance(self.tags_at_time, list):
                tags_list = self.tags_at_time

        return {
            'id': self.id,
            'transcription_id': self.transcription_id,
            'api_endpoint': self.api_endpoint,
            'model': self.model,
            'api_key_used': self.api_key_used,
            'system_prompt': self.system_prompt,
            'tags_at_time': tags_list,
            'config_source': self.config_source,
            'summary_text': self.summary_text,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'generation_time_ms': self.generation_time_ms,
            'prompt_tokens': self.prompt_tokens,
            'completion_tokens': self.completion_tokens,
        }


# Indexes for Transcription
Index('idx_status', Transcription.status)
Index('idx_created_at', Transcription.created_at.desc())
Index('idx_transcribed_at', Transcription.transcribed_at.desc())
Index('idx_cached_until', Transcription.audio_cached_until)
Index('idx_source_type', Transcription.source_type)

# Indexes for Summary
Index('idx_summary_transcription_id', Summary.transcription_id)
Index('idx_summary_created_at', Summary.created_at.desc())
