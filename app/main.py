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
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from PIL import Image, ImageGrab
import logging
from selenium import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

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

# Mount static files for noVNC if directory exists
if os.path.exists("/app/static"):
    app.mount("/static", StaticFiles(directory="/app/static"), name="static")

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

class NavigateRequest(BaseModel):
    url: str
    wait_ms: Optional[int] = 2000

class ClickRequest(BaseModel):
    selector: str

class TypeRequest(BaseModel):
    selector: str
    text: str

driver: Optional[webdriver.Firefox] = None

def get_driver() -> webdriver.Firefox:
    global driver
    if driver is not None:
        try:
            # Check if driver is still alive
            driver.current_url
            return driver
        except:
            # Driver is dead, recreate it
            driver = None
    
    logger.info("Creating new Firefox driver with display :0")
    opts = FirefoxOptions()
    # DO NOT use headless mode - we want to see the browser!
    # opts.add_argument("--headless")
    
    # Use Xvfb display
    os.environ["DISPLAY"] = ":0"
    
    # Add preferences for better compatibility
    opts.set_preference("browser.download.folderList", 2)
    opts.set_preference("browser.download.manager.showWhenStarting", False)
    opts.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/octet-stream")
    
    try:
        driver = webdriver.Firefox(options=opts)
        driver.set_page_load_timeout(30)
        driver.set_window_size(1920, 1080)
        logger.info("Firefox driver created successfully")
        return driver
    except Exception as e:
        logger.error(f"Failed to create Firefox driver: {e}")
        raise

@app.get("/")
async def root():
    return {"message": "Paladin Linux Sandbox API", "status": "running"}

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check sandbox health and availability."""
    try:
        # Check if X server is running by checking the display socket
        display_check = os.path.exists("/tmp/.X11-unix/X0")
        desktop_running = display_check
        
        # Check if VNC is accessible by checking process
        vnc_check = subprocess.run(
            ["pgrep", "-f", "x11vnc"],
            capture_output=True,
            timeout=5
        )
        vnc_available = vnc_check.returncode == 0
        
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

@app.post("/browser/navigate")
async def browser_navigate(req: NavigateRequest):
    try:
        logger.info(f"Browser navigate requested to: {req.url}")
        d = get_driver()
        
        # Log current state
        current_url = d.current_url
        logger.info(f"Current URL before navigation: {current_url}")
        
        # Navigate to the URL
        d.get(req.url)
        logger.info(f"Navigation command sent to browser")
        
        # Wait for page to load
        wait_time = (req.wait_ms or 2000) / 1000
        logger.info(f"Waiting {wait_time} seconds for page to load")
        time.sleep(wait_time)
        
        # Verify navigation
        new_url = d.current_url
        logger.info(f"Current URL after navigation: {new_url}")
        
        # Take a screenshot after navigation for debugging
        try:
            screenshot_path = f"/tmp/nav_{int(time.time())}.png"
            d.save_screenshot(screenshot_path)
            logger.info(f"Screenshot saved to {screenshot_path}")
        except Exception as ss_error:
            logger.warning(f"Failed to save debug screenshot: {ss_error}")
        
        return {"success": True, "url": new_url}
    except Exception as e:
        logger.error(f"Browser navigation failed: {e}")
        return {"success": False, "error": str(e)}

@app.post("/browser/click")
async def browser_click(req: ClickRequest):
    try:
        d = get_driver()
        el = d.find_element(By.CSS_SELECTOR, req.selector)
        el.click()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/browser/type")
async def browser_type(req: TypeRequest):
    try:
        d = get_driver()
        el = d.find_element(By.CSS_SELECTOR, req.selector)
        el.clear()
        el.send_keys(req.text)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/browser/page_content")
async def browser_page_content():
    try:
        d = get_driver()
        return {"success": True, "content": d.page_source[:200000]}
    except Exception as e:
        return {"success": False, "error": str(e)}

class FindRequest(BaseModel):
    selector: str

@app.post("/browser/find")
async def browser_find(req: FindRequest):
    try:
        d = get_driver()
        elements = d.find_elements(By.CSS_SELECTOR, req.selector)
        # Return simple index-based selectors for reuse
        selectors = []
        for idx, _ in enumerate(elements):
            selectors.append(f"{req.selector}:nth-of-type({idx+1})")
        return {"success": True, "selectors": selectors, "count": len(elements)}
    except Exception as e:
        return {"success": False, "error": str(e), "selectors": [], "count": 0}

class KeyRequest(BaseModel):
    key: str

@app.post("/browser/press_key")
async def browser_press_key(req: KeyRequest):
    try:
        d = get_driver()
        active = d.switch_to.active_element
        key = req.key
        # Map common keys
        key_map = {
            "Enter": Keys.ENTER,
            "Tab": Keys.TAB,
            "Escape": Keys.ESCAPE,
            "Backspace": Keys.BACKSPACE
        }
        send = key_map.get(key, key)
        active.send_keys(send)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/browser/alert_present")
async def browser_alert_present():
    try:
        d = get_driver()
        try:
            d.switch_to.alert
            return {"present": True}
        except Exception:
            return {"present": False}
    except Exception as e:
        return {"present": False, "error": str(e)}

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

@app.get("/vnc.html")
async def vnc_redirect():
    """Redirect to noVNC viewer."""
    host = os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'localhost')
    return RedirectResponse(url=f"/static/vnc.html?autoconnect=true&host={host}&port=443&encrypt=true&path=websockify")

@app.get("/vnc-info")
async def get_vnc_info():
    """Get VNC connection information."""
    host = os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'localhost')
    return {
        "vnc_host": "0.0.0.0",
        "vnc_port": 5900,
        "novnc_port": 6080,
        "novnc_url": f"https://{host}/vnc.html",
        "password_required": False,
        "display": ":0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
