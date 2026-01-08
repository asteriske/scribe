#!/bin/bash
# Start script for emailer service

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Creating..."
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "No .env file found. Copying from .env.example..."
    cp .env.example .env
    echo "Please edit .env with your configuration"
fi

# Check if .secrets exists
if [ ! -f ".secrets" ]; then
    if [ -f ".secrets.example" ]; then
        echo "No .secrets file found. Copying from .secrets.example..."
        cp .secrets.example .secrets
        echo "Please edit .secrets with your credentials"
    fi
fi

# Check if frontend service is running
echo "Checking frontend service..."
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo "Warning: Frontend service not responding at http://localhost:8000"
    echo "Make sure the frontend service is running before starting emailer"
fi

# Start the service
echo "Starting emailer service..."
python -m emailer.main
