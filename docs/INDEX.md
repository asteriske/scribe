# Scribe Documentation Index

Welcome to the Scribe documentation! This index will help you find the information you need.

## Quick Links

- **[Main README](../README.md)** - Project overview and quick start
- **[Setup Guide](SETUP.md)** - Installation and configuration
- **[Architecture](ARCHITECTURE.md)** - System design and data flow
- **[API Reference](API.md)** - Complete API documentation
- **[Database Schema](DATABASE.md)** - Database structure and models
- **[Development Guide](DEVELOPMENT.md)** - Contributing and development workflow

## Getting Started

### For Users

1. Start with the **[Main README](../README.md)** for an overview
2. Follow the **[Setup Guide](SETUP.md)** to install and configure
3. Check the **[Architecture](ARCHITECTURE.md)** to understand how it works

### For Developers

1. Read the **[Development Guide](DEVELOPMENT.md)** for setup
2. Review the **[Architecture](ARCHITECTURE.md)** to understand the system
3. Check the **[API Reference](API.md)** for endpoint details
4. See the **[Database Schema](DATABASE.md)** for data models
5. Read **[CONTRIBUTING.md](../CONTRIBUTING.md)** for contribution guidelines

## Documentation by Topic

### Installation & Setup
- [Setup Guide](SETUP.md) - Complete setup instructions
- [Configuration](SETUP.md#configuration) - Environment variables and settings
- [Deployment Scenarios](SETUP.md#deployment-scenarios) - Different deployment options
- [Troubleshooting](SETUP.md#troubleshooting) - Common issues and solutions

### Architecture & Design
- [System Overview](ARCHITECTURE.md#system-design) - Component architecture
- [Data Flow](ARCHITECTURE.md#data-flow) - Complete workflow
- [Communication Protocol](ARCHITECTURE.md#communication-protocol) - Service interaction
- [Storage Architecture](ARCHITECTURE.md#storage-architecture) - File and database structure
- [Scalability](ARCHITECTURE.md#scalability-considerations) - Future scaling options

### API Documentation
- [Frontend API](API.md#frontend-api-port-8000) - Web UI and REST endpoints
- [Transcriber API](API.md#transcriber-api-port-8001) - Internal transcription service
- [WebSocket API](API.md#websocket-routes) - Real-time updates
- [Error Responses](API.md#error-responses) - Error handling

### Database
- [Schema](DATABASE.md#schema) - Table definitions
- [Data Models](DATABASE.md#data-models-sqlalchemy) - SQLAlchemy models
- [JSON Format](DATABASE.md#transcription-json-format) - Transcription file structure
- [Queries](DATABASE.md#common-queries) - Example queries
- [Full-Text Search](DATABASE.md#virtual-table-transcriptions_fts) - Search implementation

### Development
- [Development Setup](DEVELOPMENT.md#development-setup) - Dev environment
- [Project Structure](DEVELOPMENT.md#project-structure) - Code organization
- [Testing](DEVELOPMENT.md#testing) - Writing and running tests
- [Code Style](DEVELOPMENT.md#code-style) - Coding standards
- [Debugging](DEVELOPMENT.md#debugging) - Debug techniques
- [Adding Features](DEVELOPMENT.md#adding-features) - Feature development guide

## Documentation by User Type

### End Users
**"I just want to use Scribe to transcribe videos"**

1. [Quick Start](../README.md#quick-start) - Get up and running
2. [Usage Guide](../README.md#usage) - How to use the web interface
3. [Troubleshooting](SETUP.md#troubleshooting) - Fix common problems

### System Administrators
**"I need to deploy Scribe for my team"**

1. [Prerequisites](SETUP.md#prerequisites) - System requirements
2. [Installation](SETUP.md#installation) - Install steps
3. [Configuration](SETUP.md#configuration) - Environment setup
4. [Deployment](SETUP.md#production-mode) - Production deployment
5. [Monitoring](ARCHITECTURE.md#monitoring--observability) - Health checks and logs
6. [Backup & Recovery](DATABASE.md#backup--recovery) - Data protection

### Developers
**"I want to contribute or customize Scribe"**

1. [Development Setup](DEVELOPMENT.md#development-setup) - Dev environment
2. [Architecture Overview](ARCHITECTURE.md) - Understand the system
3. [API Reference](API.md) - Endpoint details
4. [Database Schema](DATABASE.md) - Data structure
5. [Testing Guide](DEVELOPMENT.md#testing) - Write tests
6. [Contributing Guidelines](../CONTRIBUTING.md) - Contribution process

### Integrators
**"I want to integrate Scribe with other tools"**

1. [Frontend API](API.md#frontend-api-port-8000) - REST API endpoints
2. [WebSocket API](API.md#websocket-routes) - Real-time updates
3. [JSON Format](DATABASE.md#transcription-json-format) - Output format
4. [Export Formats](API.md#get-apitranscriptionsidexportformat) - Available formats

## Common Tasks

### Setup & Configuration
- [Install transcriber service](SETUP.md#2-set-up-transcriber-service-macos-machine)
- [Install frontend service](SETUP.md#3-set-up-frontend-service-any-machine)
- [Configure environment variables](SETUP.md#configuration)
- [Deploy on separate machines](SETUP.md#scenario-2-separate-machines-recommended)

### Usage
- [Submit a URL for transcription](../README.md#usage)
- [View transcriptions](API.md#get-apitranscriptionsid)
- [Search transcriptions](API.md#get-apisearch)
- [Export transcription](API.md#get-apitranscriptionsidexportformat)

### Development
- [Run in development mode](DEVELOPMENT.md#running-in-development-mode)
- [Run tests](DEVELOPMENT.md#running-tests)
- [Add a new download source](DEVELOPMENT.md#adding-a-new-download-source)
- [Add a new export format](DEVELOPMENT.md#adding-a-new-export-format)

### Maintenance
- [View logs](SETUP.md#log-files)
- [Clear cache](DEVELOPMENT.md#clear-cache)
- [Backup database](DATABASE.md#backup)
- [Update Scribe](SETUP.md#updating)

## File Reference

### Project Root
```
scribe/
├── README.md                    # Project overview
├── LICENSE                      # MIT License
├── CHANGELOG.md                 # Version history
├── CONTRIBUTING.md              # Contribution guidelines
├── .gitignore                   # Git ignore rules
│
├── docs/                        # Documentation
│   ├── INDEX.md                # This file
│   ├── ARCHITECTURE.md         # System architecture
│   ├── API.md                  # API specifications
│   ├── DATABASE.md             # Database schema
│   ├── SETUP.md                # Setup and deployment
│   └── DEVELOPMENT.md          # Development guide
│
├── transcriber/                # Transcription service
│   ├── .env.example           # Configuration template
│   └── ...
│
├── frontend/                   # Frontend service
│   ├── .env.example           # Configuration template
│   └── ...
│
└── data/                       # Data directory
    ├── scribe.db              # SQLite database
    ├── transcriptions/        # JSON outputs
    ├── cache/                 # Temporary audio
    └── logs/                  # Log files
```

## External Resources

### Dependencies
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [MLX Documentation](https://ml-explore.github.io/mlx/)
- [yt-dlp Documentation](https://github.com/yt-dlp/yt-dlp)
- [Whisper Paper](https://arxiv.org/abs/2212.04356)

### Related Projects
- [MLX Whisper](https://github.com/ml-explore/mlx-examples/tree/main/whisper)
- [OpenAI Whisper](https://github.com/openai/whisper)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)

## Getting Help

- **Documentation**: Start with this index
- **Issues**: Check [GitHub Issues](../../issues)
- **Questions**: Open a `question` issue
- **Bugs**: See [CONTRIBUTING.md](../CONTRIBUTING.md#reporting-bugs)
- **Features**: See [CONTRIBUTING.md](../CONTRIBUTING.md#suggesting-enhancements)

## Document Status

| Document | Status | Last Updated |
|----------|--------|--------------|
| README.md | Complete | 2026-01-02 |
| ARCHITECTURE.md | Complete | 2026-01-02 |
| API.md | Complete | 2026-01-02 |
| DATABASE.md | Complete | 2026-01-02 |
| SETUP.md | Complete | 2026-01-02 |
| DEVELOPMENT.md | Complete | 2026-01-02 |
| INDEX.md | Complete | 2026-01-02 |

## Next Steps

Choose your path:

- **New User?** → [README](../README.md) → [Setup Guide](SETUP.md)
- **Developer?** → [Development Guide](DEVELOPMENT.md) → [Architecture](ARCHITECTURE.md)
- **Integrator?** → [API Reference](API.md) → [Database Schema](DATABASE.md)
- **Contributor?** → [CONTRIBUTING.md](../CONTRIBUTING.md) → [Development Guide](DEVELOPMENT.md)

---

**Last Updated**: 2026-01-02
**Version**: 0.1.0 (unreleased)
