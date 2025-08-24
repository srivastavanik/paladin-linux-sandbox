#!/bin/bash

# Minimal Paladin Linux Sandbox (API-only)
# For memory-constrained environments

echo "Starting Minimal Paladin Linux Sandbox (API-only)..."

# Start only essential services for API functionality
export DISPLAY=:99

# Start minimal X server (no desktop)
echo "Starting minimal Xvfb..."
Xvfb :99 -screen 0 1024x768x16 -nolisten tcp &
sleep 1

# Start FastAPI server immediately (highest priority)
echo "Starting FastAPI server..."
cd /app
exec python3 -m uvicorn main:app --host 0.0.0.0 --port 8080 --log-level info
