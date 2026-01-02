# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Full-text search across transcriptions
- Batch processing of YouTube playlists
- RAG integration for question-answering
- Speaker diarization
- Summary generation
- Additional export formats
- User authentication
- API key support

## [0.1.0] - TBD

### Added
- Initial project setup and architecture design
- Transcriber service with MLX Whisper support
- Frontend service with web interface
- Support for YouTube videos
- Support for Apple Podcasts
- Support for direct audio URLs (.mp3, .m4a)
- SQLite database for metadata
- JSON export format with timestamps
- TXT export format
- SRT subtitle export format
- Audio caching with configurable retention
- Real-time progress updates via WebSocket
- Automatic cleanup of expired audio files
- Full API documentation
- Comprehensive setup and development guides

### Configuration
- Whisper model: medium (default)
- Audio cache retention: 7 days
- No authentication (trusted network)
- SQLite database storage

---

## Version History Legend

- **Added** - New features
- **Changed** - Changes in existing functionality
- **Deprecated** - Soon-to-be removed features
- **Removed** - Removed features
- **Fixed** - Bug fixes
- **Security** - Security improvements

---

## Future Versions

### [0.2.0] - Planned
- Full-text search implementation
- Improved error handling
- Progress indicators in UI
- Batch processing capability

### [0.3.0] - Planned
- User authentication
- Multiple user support
- Tags and categories
- Analytics dashboard

### [1.0.0] - Planned
- Production-ready release
- Complete test coverage
- Performance optimizations
- Database migrations support
- Comprehensive monitoring
