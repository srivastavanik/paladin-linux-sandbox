#!/usr/bin/env python3
"""
Mock Linux Sandbox API Server
Provides API endpoints for development/cloud environments where full sandboxes aren't available.
"""

import os
import time
import base64
from typing import Dict, Any, Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Mock Paladin Linux Sandbox API", version="1.0.0")

# Enable CORS for all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CommandRequest(BaseModel):
    command: str
    timeout: Optional[int] = 30
    background: Optional[bool] = False

class CommandResult(BaseModel):
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    error: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    sandbox_type: str
    desktop_running: bool
    vnc_available: bool
    api_version: str

class ScreenshotResponse(BaseModel):
    success: bool
    image_data: Optional[str] = None
    format: str = "png"
    timestamp: float
    error: Optional[str] = None

@app.get("/")
async def root():
    return {
        "message": "Mock Paladin Linux Sandbox API", 
        "status": "running",
        "mode": "mock",
        "warning": "This is a mock sandbox for development/cloud environments"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Mock health check - always returns healthy for demo purposes."""
    logger.info("Mock health check requested")
    return HealthResponse(
        status="healthy",
        sandbox_type="linux-mock",
        desktop_running=True,  # Mock as if desktop is running
        vnc_available=True,    # Mock as if VNC is available
        api_version="1.0.0"
    )

@app.post("/command", response_model=CommandResult)
async def execute_command(request: CommandRequest):
    """Mock command execution - simulates basic commands."""
    logger.info(f"Mock command execution: {request.command}")
    
    # Simulate common commands with mock responses
    if "whoami" in request.command.lower():
        return CommandResult(
            success=True,
            stdout="sandbox",
            stderr="",
            exit_code=0
        )
    elif "pwd" in request.command.lower():
        return CommandResult(
            success=True,
            stdout="/home/sandbox",
            stderr="",
            exit_code=0
        )
    elif "ls" in request.command.lower():
        return CommandResult(
            success=True,
            stdout="Desktop\nDownloads\nDocuments",
            stderr="",
            exit_code=0
        )
    elif "firefox" in request.command.lower() or "browser" in request.command.lower():
        return CommandResult(
            success=True,
            stdout="Mock browser started in background",
            stderr="",
            exit_code=0
        )
    else:
        # Generic success response for other commands
        return CommandResult(
            success=True,
            stdout=f"Mock execution of: {request.command}",
            stderr="",
            exit_code=0
        )

@app.get("/screenshot", response_model=ScreenshotResponse)
async def take_screenshot():
    """Mock screenshot - returns a small placeholder image."""
    logger.info("Mock screenshot requested")
    
    # Create a small 1x1 PNG pixel as base64 (placeholder)
    # This is a minimal valid PNG image
    placeholder_png_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAI9jINnFQAAAABJRU5ErkJggg=="
    
    return ScreenshotResponse(
        success=True,
        image_data=placeholder_png_b64,
        format="png",
        timestamp=time.time()
    )

@app.get("/status")
async def get_status():
    """Mock detailed sandbox status."""
    logger.info("Mock status requested")
    
    return {
        "sandbox_type": "linux-mock",
        "status": "running",
        "mode": "mock",
        "uptime": "Mock uptime: up for development",
        "disk_usage": "Mock disk usage: 10% used",
        "top_processes": [
            {"pid": "1", "cpu": "0.1", "mem": "1.0", "command": "mock-process"},
            {"pid": "2", "cpu": "0.0", "mem": "0.5", "command": "mock-desktop"}
        ],
        "environment": {
            "display": ":99",
            "home": "/home/sandbox",
            "user": "sandbox"
        },
        "capabilities": [
            "mock_command_execution",
            "mock_screenshot_capture", 
            "mock_desktop_gui",
            "development_testing"
        ],
        "warning": "This is a mock sandbox for development/cloud environments"
    }

@app.get("/vnc-info")
async def get_vnc_info():
    """Mock VNC connection information."""
    return {
        "vnc_host": "mock-host",
        "vnc_port": 5900,
        "novnc_port": 6080,
        "novnc_url": "/mock-vnc-not-available",
        "password_required": False,
        "display": ":99",
        "warning": "VNC not available in mock mode"
    }

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Mock Paladin Linux Sandbox API")
    uvicorn.run(app, host="0.0.0.0", port=8080)
