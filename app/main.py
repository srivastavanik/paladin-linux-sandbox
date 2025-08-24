#!/usr/bin/env python3
"""
Linux Sandbox API Server
Implements the sandbox interface for remote desktop testing.
"""

import os
import subprocess
import tempfile
import time
import base64
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from PIL import Image, ImageGrab
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Paladin Linux Sandbox API", version="1.0.0")

# Enable CORS for all origins (adjust in production)
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
    return {"message": "Paladin Linux Sandbox API", "status": "running"}

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check sandbox health and availability."""
    try:
        # Check if X server is running
        display_check = subprocess.run(
            ["xdpyinfo", "-display", ":0"],
            capture_output=True,
            timeout=5
        )
        desktop_running = display_check.returncode == 0
        
        # Check if VNC is accessible
        vnc_check = subprocess.run(
            ["netstat", "-ln"],
            capture_output=True,
            timeout=5
        )
        vnc_available = ":5900" in vnc_check.stdout.decode()
        
        return HealthResponse(
            status="healthy",
            sandbox_type="linux",
            desktop_running=desktop_running,
            vnc_available=vnc_available,
            api_version="1.0.0"
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            sandbox_type="linux", 
            desktop_running=False,
            vnc_available=False,
            api_version="1.0.0"
        )

@app.post("/command", response_model=CommandResult)
async def execute_command(request: CommandRequest):
    """Execute a command in the sandbox."""
    try:
        logger.info(f"Executing command: {request.command}")
        
        # Set up environment for GUI applications
        env = os.environ.copy()
        env["DISPLAY"] = ":0"
        env["HOME"] = "/home/sandbox"
        
        if request.background:
            # Run command in background
            process = subprocess.Popen(
                request.command,
                shell=True,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            return CommandResult(
                success=True,
                stdout=f"Command started in background (PID: {process.pid})",
                stderr="",
                exit_code=0
            )
        else:
            # Run command and wait for completion
            result = subprocess.run(
                request.command,
                shell=True,
                env=env,
                capture_output=True,
                text=True,
                timeout=request.timeout,
                cwd="/home/sandbox"
            )
            
            return CommandResult(
                success=result.returncode == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode
            )
            
    except subprocess.TimeoutExpired:
        return CommandResult(
            success=False,
            stdout="",
            stderr="Command timed out",
            exit_code=-1,
            error="Command execution timed out"
        )
    except Exception as e:
        logger.error(f"Command execution failed: {e}")
        return CommandResult(
            success=False,
            stdout="",
            stderr=str(e),
            exit_code=-1,
            error=f"Command execution failed: {e}"
        )

@app.get("/screenshot", response_model=ScreenshotResponse)
async def take_screenshot():
    """Take a screenshot of the desktop."""
    try:
        # Use xwd to capture the screen
        with tempfile.NamedTemporaryFile(suffix=".xwd", delete=False) as temp_file:
            temp_path = temp_file.name
        
        # Capture screen using xwd
        result = subprocess.run([
            "xwd", "-display", ":0", "-root", "-out", temp_path
        ], capture_output=True, timeout=10)
        
        if result.returncode != 0:
            return ScreenshotResponse(
                success=False,
                timestamp=time.time(),
                error="Screenshot capture failed"
            )
        
        # Convert XWD to PNG using ImageMagick convert
        png_path = temp_path.replace(".xwd", ".png")
        convert_result = subprocess.run([
            "convert", temp_path, png_path
        ], capture_output=True, timeout=10)
        
        if convert_result.returncode != 0:
            # Fallback: try to read XWD directly (less reliable)
            try:
                with open(temp_path, "rb") as f:
                    image_data = base64.b64encode(f.read()).decode()
                os.unlink(temp_path)
                return ScreenshotResponse(
                    success=True,
                    image_data=image_data,
                    format="xwd",
                    timestamp=time.time()
                )
            except Exception as e:
                return ScreenshotResponse(
                    success=False,
                    timestamp=time.time(),
                    error=f"Screenshot conversion failed: {e}"
                )
        
        # Read the PNG file
        try:
            with open(png_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode()
            
            # Cleanup temp files
            os.unlink(temp_path)
            os.unlink(png_path)
            
            return ScreenshotResponse(
                success=True,
                image_data=image_data,
                format="png",
                timestamp=time.time()
            )
        except Exception as e:
            return ScreenshotResponse(
                success=False,
                timestamp=time.time(),
                error=f"Failed to read screenshot: {e}"
            )
            
    except Exception as e:
        logger.error(f"Screenshot failed: {e}")
        return ScreenshotResponse(
            success=False,
            timestamp=time.time(),
            error=f"Screenshot failed: {e}"
        )

@app.get("/status")
async def get_status():
    """Get detailed sandbox status."""
    try:
        # Get system information
        uptime_result = subprocess.run(["uptime"], capture_output=True, text=True)
        df_result = subprocess.run(["df", "-h"], capture_output=True, text=True)
        ps_result = subprocess.run(["ps", "aux"], capture_output=True, text=True)
        
        # Check running processes
        processes = []
        if ps_result.returncode == 0:
            lines = ps_result.stdout.split('\n')[1:]  # Skip header
            for line in lines[:10]:  # Top 10 processes
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 11:
                        processes.append({
                            "pid": parts[1],
                            "cpu": parts[2],
                            "mem": parts[3],
                            "command": " ".join(parts[10:])[:50]
                        })
        
        return {
            "sandbox_type": "linux",
            "status": "running",
            "uptime": uptime_result.stdout.strip() if uptime_result.returncode == 0 else "unknown",
            "disk_usage": df_result.stdout if df_result.returncode == 0 else "unknown",
            "top_processes": processes,
            "environment": {
                "display": os.environ.get("DISPLAY", "not set"),
                "home": os.environ.get("HOME", "not set"),
                "user": os.environ.get("USER", "not set")
            },
            "capabilities": [
                "command_execution",
                "screenshot_capture",
                "desktop_gui",
                "web_browsers",
                "file_operations"
            ]
        }
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return {
            "sandbox_type": "linux",
            "status": "error",
            "error": str(e)
        }

@app.get("/vnc-info")
async def get_vnc_info():
    """Get VNC connection information."""
    return {
        "vnc_host": "0.0.0.0",
        "vnc_port": 5900,
        "novnc_port": 6080,
        "novnc_url": f"/static/vnc.html?host={os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'localhost')}&port=6080",
        "password_required": False,
        "display": ":0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
