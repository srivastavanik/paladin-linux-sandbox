# Ubuntu Desktop Sandbox with VNC and API
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV DISPLAY=:0
ENV VNC_PORT=5900
ENV NOVNC_PORT=6080
ENV API_PORT=8080

# Install minimal desktop and VNC (optimized for low memory)
RUN apt-get update && apt-get install -y \
    fluxbox \
    x11vnc xvfb \
    websockify \
    python3 python3-pip \
    curl wget \
    firefox \
    imagemagick \
    nano \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Install Python dependencies
RUN pip3 install fastapi uvicorn pillow requests python-multipart

# Create non-root user
RUN useradd -m -s /bin/bash sandbox && \
    echo "sandbox:sandbox" | chpasswd && \
    usermod -aG sudo sandbox

# Create app directory
WORKDIR /app

# Copy FastAPI server
COPY app/ /app/

# Create noVNC static files directory
RUN mkdir -p /app/static

# Download noVNC
RUN wget -qO- https://github.com/novnc/noVNC/archive/v1.4.0.tar.gz | tar xz && \
    mv noVNC-1.4.0/* /app/static/ && \
    rm -rf noVNC-1.4.0

# Create startup script
COPY start.sh /start.sh
RUN chmod +x /start.sh

# Expose ports
EXPOSE 8080 6080

# Start services
CMD ["/start.sh"]
