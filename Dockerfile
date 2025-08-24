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
    ca-certificates \
    libgtk-3-0 libdbus-glib-1-2 libxt6 libx11-xcb1 libasound2 libnss3 libxss1 \
    libx11-6 libxcb1 libxcomposite1 libxcursor1 libxdamage1 libxi6 libxtst6 \
    libglib2.0-0 libpango-1.0-0 libatk-bridge2.0-0 libgbm1 \
    imagemagick \
    nano \
    net-tools \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Install Firefox (official tarball) and geckodriver
ENV GECKODRIVER_VERSION=0.34.0
RUN wget -O /tmp/firefox.tar.bz2 "https://download.mozilla.org/?product=firefox-latest&os=linux64&lang=en-US" \
    && tar -xjf /tmp/firefox.tar.bz2 -C /opt \
    && ln -sf /opt/firefox/firefox /usr/local/bin/firefox \
    && wget -O /tmp/geckodriver.tar.gz https://github.com/mozilla/geckodriver/releases/download/v${GECKODRIVER_VERSION}/geckodriver-v${GECKODRIVER_VERSION}-linux64.tar.gz \
    && tar -xzf /tmp/geckodriver.tar.gz -C /usr/local/bin \
    && chmod +x /usr/local/bin/geckodriver \
    && rm -f /tmp/firefox.tar.bz2 /tmp/geckodriver.tar.gz

# Install Python dependencies
RUN pip3 install fastapi uvicorn pillow requests python-multipart selenium

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
