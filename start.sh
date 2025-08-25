#!/bin/bash

# Start Paladin Linux Sandbox Services

echo "Starting Paladin Linux Sandbox..."

# Respect Render's PORT for primary HTTP service
PORT=${PORT:-8080}

# Start FastAPI API FIRST on the primary port so Render binds correctly
echo "Starting FastAPI server on port ${PORT}..."
cd /app
python3 -m uvicorn main:app --host 0.0.0.0 --port ${PORT} --log-level info &

# Start Xvfb (virtual framebuffer)
echo "Starting Xvfb..."
Xvfb :0 -screen 0 1920x1080x24 -nolisten tcp &
export DISPLAY=:0

# Start window manager
echo "Starting Fluxbox desktop..."
fluxbox &

# Start VNC server
echo "Starting x11vnc..."
x11vnc -display :0 -forever -shared -nopw -rfbport 5900 -quiet &

# Create log directory if it doesn't exist
mkdir -p /var/log/paladin

# Start websockify for noVNC (secondary port)
echo "Starting websockify for noVNC on 6080..."
websockify --web=/app/static 0.0.0.0:6080 localhost:5900 &

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

# FastAPI already started above on ${PORT}

echo "All services started!"
echo "API Server: http://0.0.0.0:${PORT}"
echo "noVNC: http://0.0.0.0:6080/vnc.html"
echo "VNC Direct: localhost:5900"

# Keep container running and monitor services
while true; do
    # Check if FastAPI is still running
    if ! pgrep -f "uvicorn main:app" > /dev/null; then
        echo "FastAPI server stopped! Restarting..."
        cd /app
        python3 -m uvicorn main:app --host 0.0.0.0 --port ${PORT} --log-level info &
    fi
    
    # Check other critical services
    if ! pgrep -f "Xvfb" > /dev/null; then
        echo "Xvfb stopped! Restarting..."
        Xvfb :0 -screen 0 1920x1080x24 -nolisten tcp &
    fi
    
    if ! pgrep -f "x11vnc" > /dev/null; then
        echo "x11vnc stopped! Restarting..."
        x11vnc -display :0 -forever -shared -nopw -rfbport 5900 -quiet &
    fi
    
    if ! pgrep -f "websockify" > /dev/null; then
        echo "websockify stopped! Restarting..."
        websockify --web=/app/static 0.0.0.0:6080 localhost:5900 --log-file=/var/log/paladin/websockify.log &
    fi
    
    sleep 10
done
