# Paladin Linux Sandbox Service

Standalone Linux desktop sandbox with VNC viewer and REST API for remote security testing.

## Features

- Ubuntu 22.04 with XFCE desktop
- VNC server for remote desktop access
- noVNC web-based viewer
- FastAPI REST interface
- Pre-installed browsers and tools

## API Endpoints

- `GET /health` - Health check
- `POST /command` - Execute commands
- `GET /screenshot` - Capture desktop
- `GET /status` - System status
- `GET /vnc-info` - VNC connection info

## Ports

- 8080: FastAPI server
- 6080: noVNC web viewer  
- 5900: VNC server (internal)

## Local Testing

```bash
docker build -t paladin-linux-sandbox .
docker run -p 8080:8080 -p 6080:6080 paladin-linux-sandbox
```

Access:
- API: http://localhost:8080
- Desktop: http://localhost:6080/vnc.html

## Render Deployment

1. Push this directory to a Git repository
2. Create new Render Web Service
3. Connect repository
4. Set Dockerfile path: `./Dockerfile`
5. Deploy

The service will be available at your Render URL with both API and VNC access.
