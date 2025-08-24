#!/bin/bash

# Start Paladin Linux Sandbox Services

echo "Starting Paladin Linux Sandbox..."

# Start Xvfb (virtual framebuffer)
echo "Starting Xvfb..."
Xvfb :0 -screen 0 1920x1080x24 -nolisten tcp &
export DISPLAY=:0

# Wait for X server to start
sleep 2

# Start window manager
echo "Starting Fluxbox desktop..."
fluxbox &

# Wait for desktop to start
sleep 3

# Start VNC server
echo "Starting x11vnc..."
x11vnc -display :0 -forever -shared -nopw -rfbport 5900 -quiet &

# Wait for VNC to start
sleep 2

# Start websockify for noVNC
echo "Starting websockify for noVNC..."
websockify --web=/app/static 0.0.0.0:6080 localhost:5900 &

# Wait for websockify to start
sleep 2

# Create sandbox user home directory
mkdir -p /home/sandbox
chown -R sandbox:sandbox /home/sandbox

# Set up some basic desktop environment
su - sandbox -c "
    export DISPLAY=:0
    mkdir -p /home/sandbox/Desktop
    mkdir -p /home/sandbox/Downloads
    echo 'Welcome to Paladin Linux Sandbox' > /home/sandbox/Desktop/README.txt
"

# Verify services are running
echo "Checking services..."
echo "X Server status:"
ps aux | grep Xvfb | grep -v grep || echo "Xvfb not running"

echo "VNC status:"
ps aux | grep x11vnc | grep -v grep || echo "x11vnc not running"

echo "noVNC status:"
ps aux | grep websockify | grep -v grep || echo "websockify not running"

echo "Port status:"
netstat -ln | grep :5900 || echo "VNC port 5900 not listening"
netstat -ln | grep :6080 || echo "noVNC port 6080 not listening"

echo "Starting FastAPI server..."
cd /app
python3 -m uvicorn main:app --host 0.0.0.0 --port 8080 --log-level info
