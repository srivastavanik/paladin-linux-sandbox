# paladin-linux-sandbox/Dockerfile
FROM mcr.microsoft.com/playwright/python:v1.45.0-jammy

ENV DEBIAN_FRONTEND=noninteractive \
    DISPLAY=":0" \
    PYTHONUNBUFFERED=1

# Desktop + viewer + CLI tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    x11vnc xvfb openbox websockify curl jq x11-apps imagemagick ffmpeg \
    git ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Security tools (light baseline)
RUN pip install --no-cache-dir \
      fastapi uvicorn sse-starlette httpx pydantic-settings \
      pillow semgrep bandit pip-audit gitleaks trivy

# App code
WORKDIR /app
COPY sandbox_api /app/sandbox_api
COPY playwright_scenarios /app/playwright_scenarios

# Download noVNC for web viewer
RUN mkdir -p /app/static && \
    wget -qO- https://github.com/novnc/noVNC/archive/v1.4.0.tar.gz | tar xz && \
    mv noVNC-1.4.0/* /app/static/ && \
    rm -rf noVNC-1.4.0

# Playwright browsers are already pre-installed in base image
EXPOSE 8080 6080

CMD bash -lc "\
  Xvfb :0 -screen 0 1920x1080x24 & \
  openbox & \
  x11vnc -display :0 -nopw -forever -shared -rfbport 5900 & \
  websockify 0.0.0.0:6080 localhost:5900 & \
  uvicorn sandbox_api.main:app --host 0.0.0.0 --port 8080"