#!/bin/bash

# Start frontend service

cd "$(dirname "$0")/.."

# Activate virtual environment
source venv/bin/activate

# Check if transcriber service is running
echo "Checking transcriber service..."
if ! curl -s http://localhost:8001/health > /dev/null; then
    echo "Warning: Transcriber service not responding at http://localhost:8001"
    echo "Make sure the transcriber service is running before submitting jobs"
fi

# Start frontend service
echo "Starting frontend service on port 8000..."
python -m frontend.main
