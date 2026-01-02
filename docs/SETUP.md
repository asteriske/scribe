# Setup & Deployment Guide

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Running the Services](#running-the-services)
5. [Deployment Scenarios](#deployment-scenarios)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Transcriber Service

**Required:**
- macOS with Apple Silicon (M1, M2, M3, or later)
- Python 3.10 or higher
- ~2GB free disk space for Whisper medium model
- ~8GB RAM (16GB recommended)

**Optional:**
- brew (for installing dependencies)

### Frontend Service

**Required:**
- Python 3.10 or higher
- ~500MB disk space for dependencies
- ~2GB RAM minimum
- Network connectivity to transcriber service

**Supported Platforms:**
- macOS (Intel or Apple Silicon)
- Linux (Ubuntu 20.04+, Debian 11+, etc.)
- Windows (via WSL2)
- Docker

---

## Installation

### 1. Clone the Repository

```bash
cd ~/git
git clone <repository-url> scribe
cd scribe
```

### 2. Set Up Transcriber Service (macOS Machine)

```bash
cd transcriber/

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Download Whisper model (optional, auto-downloads on first use)
python scripts/download_models.py --model medium
```

**Verify installation:**

```bash
python -c "import mlx; print('MLX available:', True)"
python -c "import mlx_whisper; print('MLX Whisper available:', True)"
```

### 3. Set Up Frontend Service (Any Machine)

```bash
cd frontend/

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install yt-dlp (if not already installed)
# Option 1: via pip (included in requirements.txt)
# Option 2: via brew (macOS)
brew install yt-dlp

# Option 3: standalone binary
curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o ~/.local/bin/yt-dlp
chmod +x ~/.local/bin/yt-dlp
```

**Verify installation:**

```bash
yt-dlp --version
python -c "import sqlalchemy; print('SQLAlchemy available:', True)"
python -c "import fastapi; print('FastAPI available:', True)"
```

### 4. Create Data Directory

```bash
# From project root
mkdir -p data/transcriptions data/cache/audio data/logs

# Or let the services create it automatically on first run
```

---

## Configuration

### Transcriber Service Configuration

**Create `.env` file:**

```bash
cd transcriber/
cp .env.example .env
```

**Edit `transcriber/.env`:**

```bash
# Service Configuration
HOST=0.0.0.0                    # Listen on all interfaces
PORT=8001                       # Service port
WORKERS=1                       # Number of workers (keep at 1 for MLX)
LOG_LEVEL=INFO                  # DEBUG, INFO, WARNING, ERROR

# Model Configuration
WHISPER_MODEL=medium            # tiny, base, small, medium, large-v3
MODEL_DIR=~/.cache/whisper      # Where to store model files

# Job Queue
MAX_CONCURRENT_JOBS=1           # Process one job at a time (GPU memory)
QUEUE_SIZE=10                   # Maximum queued jobs
JOB_RETENTION_HOURS=1           # How long to keep completed job results

# Performance
COMPUTE_TYPE=float16            # float16, float32 (float16 is faster)
```

**Configuration options explained:**

- **HOST**: `0.0.0.0` allows network access, `127.0.0.1` for localhost only
- **PORT**: Default 8001, change if port conflict
- **WORKERS**: Keep at 1 (MLX processes one job at a time efficiently)
- **WHISPER_MODEL**:
  - `tiny` - Fastest, least accurate (~75MB)
  - `base` - Fast, decent accuracy (~140MB)
  - `small` - Good balance (~460MB)
  - `medium` - High quality, recommended (~1.5GB)
  - `large-v3` - Best quality, slowest (~3GB)
- **MAX_CONCURRENT_JOBS**: 1 recommended (GPU memory constraint)
- **COMPUTE_TYPE**: `float16` is faster and uses less memory

---

### Frontend Service Configuration

**Create `.env` file:**

```bash
cd frontend/
cp .env.example .env
```

**Edit `frontend/.env`:**

```bash
# Service Configuration
HOST=0.0.0.0                    # Listen on all interfaces
PORT=8000                       # Service port
LOG_LEVEL=INFO                  # DEBUG, INFO, WARNING, ERROR

# Transcriber Service
TRANSCRIBER_URL=http://localhost:8001    # URL of transcriber service
# TRANSCRIBER_URL=http://192.168.1.10:8001  # If on different machine
TRANSCRIBER_TIMEOUT=300         # Request timeout in seconds
TRANSCRIBER_POLL_INTERVAL=2     # Status polling interval in seconds
TRANSCRIBER_MAX_RETRIES=3       # Number of retries on failure

# Storage
DATA_DIR=/Users/patrick/git/scribe/data  # Absolute path to data directory
AUDIO_CACHE_DAYS=7              # How long to keep audio files
MAX_AUDIO_CACHE_SIZE_GB=50      # Maximum cache size before cleanup
TRANSCRIPTION_DIR_PATTERN=%Y/%m  # Directory pattern (year/month)

# Database
DATABASE_URL=sqlite:///./data/scribe.db  # SQLite database path
# DATABASE_URL=postgresql://user:pass@host/dbname  # PostgreSQL (future)

# Downloads (yt-dlp)
YTDLP_FORMAT=bestaudio          # Download best audio quality
YTDLP_TIMEOUT=300               # Download timeout in seconds
YTDLP_MAX_FILESIZE_MB=500       # Maximum audio file size

# Supported Sources
SUPPORTED_SOURCES=youtube,apple_podcasts,direct_audio

# Cleanup
CLEANUP_INTERVAL_HOURS=6        # How often to run cleanup task
CLEANUP_ON_STARTUP=true         # Run cleanup when service starts
```

**Configuration options explained:**

- **TRANSCRIBER_URL**:
  - Same machine: `http://localhost:8001`
  - Different machine: `http://192.168.1.10:8001` (use actual IP)
  - Use hostname: `http://mac-mini.local:8001`
- **DATA_DIR**: Use absolute path, not relative
- **AUDIO_CACHE_DAYS**: Balance between storage and re-download costs
- **TRANSCRIPTION_DIR_PATTERN**:
  - `%Y/%m` - Organize by year/month (recommended)
  - `%Y` - Organize by year only
  - Empty string - Flat structure
- **DATABASE_URL**: SQLite by default, can use PostgreSQL for production
- **YTDLP_FORMAT**:
  - `bestaudio` - Best audio quality
  - `worst` - Smallest file size
  - `m4a` - Specific format

---

## Running the Services

### Development Mode

**Terminal 1 - Transcriber (macOS):**

```bash
cd transcriber/
source venv/bin/activate
python -m transcriber.main

# Or use the launch script
./scripts/start.sh
```

**Terminal 2 - Frontend (Any Machine):**

```bash
cd frontend/
source venv/bin/activate
python -m frontend.main

# Or use the launch script
./scripts/start.sh
```

**Access the web interface:**

Open browser to `http://localhost:8000`

---

### Production Mode

#### Option 1: systemd (Linux/macOS)

**Transcriber service:**

Create `/etc/systemd/system/scribe-transcriber.service`:

```ini
[Unit]
Description=Scribe Transcriber Service
After=network.target

[Service]
Type=simple
User=patrick
WorkingDirectory=/Users/patrick/git/scribe/transcriber
Environment="PATH=/Users/patrick/git/scribe/transcriber/venv/bin"
ExecStart=/Users/patrick/git/scribe/transcriber/venv/bin/python -m transcriber.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Frontend service:**

Create `/etc/systemd/system/scribe-frontend.service`:

```ini
[Unit]
Description=Scribe Frontend Service
After=network.target scribe-transcriber.service
Requires=network.target

[Service]
Type=simple
User=patrick
WorkingDirectory=/Users/patrick/git/scribe/frontend
Environment="PATH=/Users/patrick/git/scribe/frontend/venv/bin"
ExecStart=/Users/patrick/git/scribe/frontend/venv/bin/python -m frontend.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable and start:**

```bash
sudo systemctl daemon-reload
sudo systemctl enable scribe-transcriber scribe-frontend
sudo systemctl start scribe-transcriber scribe-frontend

# Check status
sudo systemctl status scribe-transcriber
sudo systemctl status scribe-frontend

# View logs
sudo journalctl -u scribe-transcriber -f
sudo journalctl -u scribe-frontend -f
```

#### Option 2: Docker (Frontend Only)

**Note:** Transcriber cannot run in Docker (requires native MLX access)

```dockerfile
# frontend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install yt-dlp dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Run application
CMD ["python", "-m", "frontend.main"]
```

**Build and run:**

```bash
cd frontend/
docker build -t scribe-frontend .
docker run -d \
  --name scribe-frontend \
  -p 8000:8000 \
  -v /path/to/data:/app/data \
  -e TRANSCRIBER_URL=http://host.docker.internal:8001 \
  scribe-frontend
```

#### Option 3: Process Manager (pm2)

```bash
# Install pm2
npm install -g pm2

# Start services
cd transcriber/
pm2 start "python -m transcriber.main" --name scribe-transcriber

cd ../frontend/
pm2 start "python -m frontend.main" --name scribe-frontend

# Save configuration
pm2 save
pm2 startup  # Follow instructions to enable on boot

# Manage services
pm2 status
pm2 logs scribe-frontend
pm2 restart scribe-transcriber
```

---

## Deployment Scenarios

### Scenario 1: All on One Mac

**Setup:**
- Both services run on same macOS machine
- Simplest configuration
- Good for personal use

**Configuration:**
```bash
# transcriber/.env
HOST=127.0.0.1
PORT=8001

# frontend/.env
TRANSCRIBER_URL=http://localhost:8001
HOST=127.0.0.1
PORT=8000
```

---

### Scenario 2: Separate Machines (Recommended)

**Setup:**
- Transcriber on macOS (192.168.1.10)
- Frontend on Linux server (192.168.1.20)
- Better resource isolation

**Transcriber configuration (macOS):**
```bash
# transcriber/.env
HOST=0.0.0.0  # Listen on all interfaces
PORT=8001
```

**Frontend configuration (Linux):**
```bash
# frontend/.env
TRANSCRIBER_URL=http://192.168.1.10:8001  # Point to macOS machine
HOST=0.0.0.0
PORT=8000
```

**Firewall:**
```bash
# On macOS, allow port 8001
sudo pfctl -e
# Or use System Preferences > Sharing > Firewall

# On Linux, allow port 8000
sudo ufw allow 8000/tcp
```

---

### Scenario 3: Frontend in Cloud

**Setup:**
- Transcriber on home macOS machine
- Frontend on cloud server (AWS/GCP/Azure)
- Requires VPN or tunnel

**Option A: Tailscale VPN**
```bash
# Install Tailscale on both machines
brew install tailscale  # macOS
# Follow: https://tailscale.com/download

# Frontend config uses Tailscale IP
TRANSCRIBER_URL=http://100.x.x.x:8001
```

**Option B: SSH Tunnel**
```bash
# On cloud server, create reverse tunnel to macOS
ssh -R 8001:localhost:8001 user@cloud-server

# Frontend config
TRANSCRIBER_URL=http://localhost:8001
```

---

## Troubleshooting

### Transcriber Issues

**Issue: Model fails to load**

```bash
# Check MLX installation
python -c "import mlx; print(mlx.__version__)"

# Reinstall MLX
pip uninstall mlx mlx-whisper
pip install mlx mlx-whisper

# Clear model cache
rm -rf ~/.cache/whisper
```

**Issue: Port 8001 already in use**

```bash
# Find process using port
lsof -i :8001

# Kill process
kill -9 <PID>

# Or change port in .env
PORT=8002
```

**Issue: Out of memory**

```bash
# Use smaller model
WHISPER_MODEL=small  # Instead of medium

# Or use base model for testing
WHISPER_MODEL=base
```

---

### Frontend Issues

**Issue: Cannot connect to transcriber**

```bash
# Test connectivity
curl http://localhost:8001/health

# Check transcriber is running
ps aux | grep transcriber

# Check firewall
sudo pfctl -s rules  # macOS
sudo ufw status      # Linux
```

**Issue: yt-dlp fails to download**

```bash
# Update yt-dlp
pip install --upgrade yt-dlp

# Or via brew
brew upgrade yt-dlp

# Test manually
yt-dlp -f bestaudio "https://youtube.com/watch?v=..."
```

**Issue: Database locked**

```bash
# Check for other processes using database
lsof data/scribe.db

# Close connections and restart service
pkill -f frontend.main
python -m frontend.main
```

**Issue: Disk full**

```bash
# Check disk space
df -h

# Manual cleanup of old audio
find data/cache/audio -mtime +7 -delete

# Reduce cache retention
AUDIO_CACHE_DAYS=1
```

---

### Network Issues

**Issue: Frontend can't reach transcriber on different machine**

```bash
# On transcriber machine, check listening
netstat -an | grep 8001

# Should show: tcp4  0  0  *.8001  *.*  LISTEN

# Ping transcriber from frontend machine
ping 192.168.1.10

# Test HTTP connectivity
curl http://192.168.1.10:8001/health
```

---

### Log Files

**Check logs:**

```bash
# Frontend logs
tail -f data/logs/frontend.log

# Transcriber logs
tail -f data/logs/transcriber.log

# Or if using systemd
journalctl -u scribe-frontend -f
journalctl -u scribe-transcriber -f
```

---

## Performance Tuning

### Transcriber

**For faster transcription:**
- Use smaller model (base or small)
- Ensure no other apps using GPU
- Close browser/other memory-intensive apps

**For better quality:**
- Use large-v3 model
- Ensure good cooling (MLX uses GPU intensively)

### Frontend

**For faster downloads:**
- Use wired connection
- Increase YTDLP_TIMEOUT for large files
- Consider download mirrors/proxies

**For lower storage:**
- Reduce AUDIO_CACHE_DAYS
- Set MAX_AUDIO_CACHE_SIZE_GB limit
- Enable cleanup on startup

---

## Updating

```bash
# Pull latest code
cd ~/git/scribe
git pull

# Update transcriber dependencies
cd transcriber/
source venv/bin/activate
pip install --upgrade -r requirements.txt

# Update frontend dependencies
cd ../frontend/
source venv/bin/activate
pip install --upgrade -r requirements.txt

# Restart services
# (use systemctl restart, pm2 restart, or manually)
```

---

## Uninstalling

```bash
# Stop services
sudo systemctl stop scribe-frontend scribe-transcriber
# Or: pm2 delete all

# Remove virtual environments
rm -rf transcriber/venv frontend/venv

# Remove data (CAUTION: deletes all transcriptions)
rm -rf data/

# Remove application
cd ..
rm -rf scribe/

# Clean up system services (if using systemd)
sudo systemctl disable scribe-frontend scribe-transcriber
sudo rm /etc/systemd/system/scribe-*.service
sudo systemctl daemon-reload
```

---

## Security Checklist

- [ ] Change default ports if exposed to internet
- [ ] Use firewall to restrict access
- [ ] Run services as non-root user
- [ ] Use HTTPS if exposing publicly (nginx reverse proxy)
- [ ] Regular backups of database
- [ ] Monitor logs for suspicious activity
- [ ] Keep dependencies updated
- [ ] Use VPN/tunnel for cloud deployments

---

## Getting Help

- **Logs**: Check `data/logs/` for error messages
- **Health endpoints**: Visit `http://localhost:8000/health` and `http://localhost:8001/health`
- **API docs**: Visit `http://localhost:8000/docs` and `http://localhost:8001/docs`
- **Issues**: Open an issue on GitHub
- **Debug mode**: Set `LOG_LEVEL=DEBUG` in `.env`
