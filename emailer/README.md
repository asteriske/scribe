# Emailer Service

Email-based job submission for Scribe transcription system.

## Overview

Monitors an IMAP folder for emails containing transcribable URLs, processes them through the frontend API, and sends results via email.

## Setup

1. Create virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. Configure environment:
   ```bash
   cp .env.example .env
   cp .secrets.example .secrets
   # Edit .env and .secrets with your settings
   ```

3. Create IMAP folders:
   - `ToScribe` - Inbox for transcription requests
   - `ScribeDone` - Completed requests
   - `ScribeError` - Failed requests

4. Run the service:
   ```bash
   python -m emailer.main
   ```

## Configuration

See `.env.example` for all configuration options.

Passwords are stored separately in `.secrets` (not committed to git).
