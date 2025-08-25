"""
Comprehensive Sandbox API with real browser automation and security tools
"""

import asyncio
import base64
import json
import logging
import os
import subprocess
import tempfile
import time
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from PIL import Image, ImageGrab
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Paladin Linux Sandbox API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request models
class ExecuteRequest(BaseModel):
    cmd: str
    timeout: int = 60
    background: bool = False

class PlaywrightRequest(BaseModel):
    scenario: str
    url: str
    payload: Optional[str] = None
    args: Dict[str, Any] = {}

class ScanRequest(BaseModel):
    target_url: Optional[str] = None
    repository_path: Optional[str] = None
    scan_type: str = "static"  # static, dynamic, sqlmap
    args: Dict[str, Any] = {}

# Global state
running_processes = {}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"ok": True, "status": "healthy", "timestamp": time.time()}

@app.get("/status")
async def get_status():
    """Get sandbox capabilities and status"""
    capabilities = {
        "vnc": True,
        "playwright": True,
        "static_analysis": True,
        "dynamic_testing": True,
        "screenshot": True,
        "command_execution": True
    }
    
    # Check if display is available
    display_available = os.environ.get('DISPLAY') is not None
    
    return {
        "ok": True,
        "capabilities": capabilities,
        "display_available": display_available,
        "running_processes": len(running_processes),
        "tools": {
            "playwright": check_tool_available("playwright"),
            "semgrep": check_tool_available("semgrep"),
            "sqlmap": check_tool_available("sqlmap"),
            "ffuf": check_tool_available("ffuf"),
            "nmap": check_tool_available("nmap")
        }
    }

def check_tool_available(tool: str) -> bool:
    """Check if a tool is available in PATH"""
    try:
        result = subprocess.run(["which", tool], capture_output=True, text=True)
        return result.returncode == 0
    except:
        return False

@app.get("/screenshot")
async def take_screenshot():
    """Take a screenshot of the desktop"""
    try:
        # Try PIL screenshot first (if running with desktop)
        if os.environ.get('DISPLAY'):
            try:
                # Use xwd to capture the screen
                result = subprocess.run([
                    "xwd", "-root", "-out", "/tmp/screenshot.xwd"
                ], capture_output=True, timeout=10)
                
                if result.returncode == 0:
                    # Convert to PNG
                    convert_result = subprocess.run([
                        "convert", "/tmp/screenshot.xwd", "/tmp/screenshot.png"
                    ], capture_output=True, timeout=10)
                    
                    if convert_result.returncode == 0:
                        with open("/tmp/screenshot.png", "rb") as f:
                            screenshot_data = f.read()
                        
                        return Response(
                            content=screenshot_data,
                            media_type="image/png",
                            headers={"Content-Disposition": "inline; filename=screenshot.png"}
                        )
            except Exception as e:
                logger.warning(f"xwd screenshot failed: {e}")
        
        # Fallback: create a simple status image
        img = Image.new('RGB', (800, 600), color='black')
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            img.save(tmp.name, 'PNG')
            with open(tmp.name, 'rb') as f:
                screenshot_data = f.read()
            os.unlink(tmp.name)
        
        return Response(
            content=screenshot_data,
            media_type="image/png",
            headers={"Content-Disposition": "inline; filename=screenshot.png"}
        )
        
    except Exception as e:
        logger.error(f"Screenshot failed: {e}")
        raise HTTPException(status_code=500, detail=f"Screenshot failed: {str(e)}")

@app.post("/execute")
async def execute_command(request: ExecuteRequest):
    """Execute a command in the sandbox"""
    try:
        logger.info(f"Executing command: {request.cmd[:100]}...")
        
        if request.background:
            # Start background process
            process = subprocess.Popen(
                request.cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            process_id = f"proc_{int(time.time())}_{process.pid}"
            running_processes[process_id] = process
            
            return {
                "success": True,
                "process_id": process_id,
                "pid": process.pid,
                "message": "Process started in background"
            }
        else:
            # Execute synchronously
            result = subprocess.run(
                request.cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=request.timeout
            )
            
            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "command": request.cmd
            }
            
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": f"Command timed out after {request.timeout} seconds",
            "command": request.cmd
        }
    except Exception as e:
        logger.error(f"Command execution failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "command": request.cmd
        }

@app.get("/execute/stream/{process_id}")
async def stream_process_output(process_id: str):
    """Stream output from a running background process"""
    if process_id not in running_processes:
        raise HTTPException(status_code=404, detail="Process not found")
    
    process = running_processes[process_id]
    
    async def generate():
        try:
            while process.poll() is None:
                # Read available output
                if process.stdout:
                    line = process.stdout.readline()
                    if line:
                        yield f"data: {json.dumps({'type': 'stdout', 'data': line})}\n\n"
                
                if process.stderr:
                    line = process.stderr.readline()
                    if line:
                        yield f"data: {json.dumps({'type': 'stderr', 'data': line})}\n\n"
                
                await asyncio.sleep(0.1)
            
            # Process finished
            yield f"data: {json.dumps({'type': 'exit', 'code': process.returncode})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'data': str(e)})}\n\n"
        finally:
            # Clean up
            if process_id in running_processes:
                del running_processes[process_id]
    
    return StreamingResponse(generate(), media_type="text/event-stream")

@app.post("/playwright")
async def run_playwright_scenario(request: PlaywrightRequest):
    """Run a Playwright automation scenario"""
    try:
        logger.info(f"Running Playwright scenario: {request.scenario} on {request.url}")
        
        # Create a temporary Python script for the scenario
        script_content = generate_playwright_script(request.scenario, request.url, request.payload, request.args)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp:
            tmp.write(script_content)
            script_path = tmp.name
        
        try:
            # Run the Playwright script
            result = subprocess.run([
                "python3", script_path
            ], capture_output=True, text=True, timeout=120)
            
            # Take a screenshot after the action
            screenshot_data = None
            try:
                screenshot_response = await take_screenshot()
                if hasattr(screenshot_response, 'body'):
                    screenshot_data = base64.b64encode(screenshot_response.body).decode()
            except:
                pass
            
            return {
                "success": result.returncode == 0,
                "scenario": request.scenario,
                "url": request.url,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "screenshot_b64": screenshot_data,
                "returncode": result.returncode
            }
            
        finally:
            os.unlink(script_path)
            
    except Exception as e:
        logger.error(f"Playwright scenario failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "scenario": request.scenario,
            "url": request.url
        }

def generate_playwright_script(scenario: str, url: str, payload: str = None, args: dict = None) -> str:
    """Generate a Playwright Python script for the given scenario"""
    args = args or {}
    
    if scenario == "navigate":
        return f"""
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        print(f"Navigating to {url}")
        response = await page.goto("{url}", timeout=30000)
        print(f"Response status: {{response.status}}")
        print(f"Final URL: {{page.url}}")
        
        # Wait for page to load
        await page.wait_for_load_state('networkidle', timeout=10000)
        
        # Get page title and basic info
        title = await page.title()
        print(f"Page title: {{title}}")
        
        # Check for common elements
        forms = await page.query_selector_all('form')
        inputs = await page.query_selector_all('input')
        links = await page.query_selector_all('a')
        
        print(f"Found {{len(forms)}} forms, {{len(inputs)}} inputs, {{len(links)}} links")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
"""
    
    elif scenario == "xss_test":
        payload = payload or "<script>alert('XSS')</script>"
        return f"""
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        # Set up dialog handler to catch alerts
        dialog_triggered = False
        def handle_dialog(dialog):
            global dialog_triggered
            dialog_triggered = True
            print(f"ALERT TRIGGERED: {{dialog.message}}")
            dialog.accept()
        
        page.on("dialog", handle_dialog)
        
        print(f"Testing XSS on {url} with payload: {payload}")
        await page.goto("{url}", timeout=30000)
        
        # Find input fields and try XSS payload
        inputs = await page.query_selector_all('input[type="text"], input[type="search"], textarea')
        
        for i, input_elem in enumerate(inputs):
            try:
                print(f"Testing input {{i+1}}/{{len(inputs)}}")
                await input_elem.fill("{payload}")
                await input_elem.press('Enter')
                await page.wait_for_timeout(1000)
                
                if dialog_triggered:
                    print("XSS VULNERABILITY DETECTED!")
                    break
                    
            except Exception as e:
                print(f"Error testing input {{i+1}}: {{e}}")
        
        # Also check URL parameters
        test_url = "{url}" + ("&" if "?" in "{url}" else "?") + f"test={payload}"
        try:
            await page.goto(test_url, timeout=10000)
            await page.wait_for_timeout(2000)
            if dialog_triggered:
                print("XSS VULNERABILITY DETECTED IN URL PARAMETER!")
        except Exception as e:
            print(f"Error testing URL parameter: {{e}}")
        
        await browser.close()
        
        if dialog_triggered:
            print("RESULT: XSS vulnerability found")
        else:
            print("RESULT: No XSS vulnerability detected")

if __name__ == "__main__":
    asyncio.run(main())
"""
    
    elif scenario == "sql_injection_test":
        payload = payload or "' OR '1'='1"
        return f"""
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        print(f"Testing SQL injection on {url} with payload: {payload}")
        await page.goto("{url}", timeout=30000)
        
        # Find forms and input fields
        forms = await page.query_selector_all('form')
        
        for form_idx, form in enumerate(forms):
            inputs = await form.query_selector_all('input[type="text"], input[type="password"], input[type="email"]')
            
            if inputs:
                print(f"Testing form {{form_idx + 1}} with {{len(inputs)}} inputs")
                
                # Fill inputs with SQL injection payload
                for input_elem in inputs:
                    await input_elem.fill("{payload}")
                
                # Submit form
                submit_btn = await form.query_selector('input[type="submit"], button[type="submit"], button')
                if submit_btn:
                    await submit_btn.click()
                    await page.wait_for_load_state('networkidle', timeout=10000)
                    
                    # Check for SQL error indicators
                    content = await page.content()
                    error_indicators = [
                        'sql syntax', 'mysql error', 'postgresql error', 'sqlite error',
                        'ora-', 'microsoft jet database', 'odbc', 'warning: mysql',
                        'error in your sql syntax', 'quoted string not properly terminated'
                    ]
                    
                    for indicator in error_indicators:
                        if indicator.lower() in content.lower():
                            print(f"SQL INJECTION VULNERABILITY DETECTED: {{indicator}}")
                            return
        
        print("RESULT: No obvious SQL injection vulnerability detected")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
"""
    
    else:
        # Generic scenario
        return f"""
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        print(f"Running scenario: {scenario}")
        await page.goto("{url}", timeout=30000)
        await page.wait_for_load_state('networkidle', timeout=10000)
        
        print("Scenario completed")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
"""

@app.post("/scan/static")
async def run_static_scan(request: ScanRequest):
    """Run static analysis on repository code"""
    if not request.repository_path:
        raise HTTPException(status_code=400, detail="repository_path required for static scan")
    
    try:
        logger.info(f"Running static scan on {request.repository_path}")
        
        results = {
            "scan_type": "static",
            "repository_path": request.repository_path,
            "findings": [],
            "tools_used": []
        }
        
        # Run Semgrep
        if check_tool_available("semgrep"):
            logger.info("Running Semgrep...")
            semgrep_result = subprocess.run([
                "semgrep", "--config=auto", "--json", "--quiet", request.repository_path
            ], capture_output=True, text=True, timeout=300)
            
            if semgrep_result.returncode == 0:
                try:
                    semgrep_data = json.loads(semgrep_result.stdout)
                    for finding in semgrep_data.get("results", []):
                        results["findings"].append({
                            "tool": "semgrep",
                            "type": finding.get("check_id", "unknown"),
                            "severity": finding.get("extra", {}).get("severity", "medium"),
                            "file": finding.get("path", ""),
                            "line": finding.get("start", {}).get("line", 0),
                            "message": finding.get("extra", {}).get("message", ""),
                            "evidence": finding.get("extra", {}).get("lines", "")
                        })
                    results["tools_used"].append("semgrep")
                except json.JSONDecodeError:
                    logger.error("Failed to parse Semgrep output")
        
        # Run Bandit for Python files
        if check_tool_available("bandit"):
            logger.info("Running Bandit...")
            bandit_result = subprocess.run([
                "bandit", "-r", request.repository_path, "-f", "json", "-q"
            ], capture_output=True, text=True, timeout=120)
            
            if bandit_result.returncode in [0, 1]:  # Bandit returns 1 when findings exist
                try:
                    bandit_data = json.loads(bandit_result.stdout)
                    for finding in bandit_data.get("results", []):
                        results["findings"].append({
                            "tool": "bandit",
                            "type": finding.get("test_id", "unknown"),
                            "severity": finding.get("issue_severity", "medium").lower(),
                            "file": finding.get("filename", ""),
                            "line": finding.get("line_number", 0),
                            "message": finding.get("issue_text", ""),
                            "evidence": finding.get("code", "")
                        })
                    results["tools_used"].append("bandit")
                except json.JSONDecodeError:
                    logger.error("Failed to parse Bandit output")
        
        logger.info(f"Static scan completed. Found {len(results['findings'])} findings")
        return results
        
    except Exception as e:
        logger.error(f"Static scan failed: {e}")
        raise HTTPException(status_code=500, detail=f"Static scan failed: {str(e)}")

@app.post("/scan/sqlmap")
async def run_sqlmap_scan(request: ScanRequest):
    """Run SQLMap scan on a target URL"""
    if not request.target_url:
        raise HTTPException(status_code=400, detail="target_url required for SQLMap scan")
    
    try:
        logger.info(f"Running SQLMap scan on {request.target_url}")
        
        # Basic SQLMap command
        cmd = [
            "sqlmap", "-u", request.target_url,
            "--batch", "--smart", "--level=2", "--risk=1",
            "--timeout=10", "--retries=1", "--threads=4",
            "--technique=BEUSTQ", "--output-dir=/tmp/sqlmap_output"
        ]
        
        # Add additional args
        if request.args.get("crawl"):
            cmd.extend(["--crawl=1"])
        if request.args.get("forms"):
            cmd.extend(["--forms"])
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        # Parse SQLMap output for vulnerabilities
        vulnerabilities = []
        if "sqlmap identified the following injection point" in result.stdout:
            vulnerabilities.append({
                "type": "sql_injection",
                "severity": "high",
                "url": request.target_url,
                "evidence": "SQLMap confirmed SQL injection vulnerability",
                "details": result.stdout
            })
        
        return {
            "scan_type": "sqlmap",
            "target_url": request.target_url,
            "vulnerabilities": vulnerabilities,
            "stdout": result.stdout[:2000],  # Truncate long output
            "stderr": result.stderr[:1000],
            "success": result.returncode == 0
        }
        
    except Exception as e:
        logger.error(f"SQLMap scan failed: {e}")
        raise HTTPException(status_code=500, detail=f"SQLMap scan failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
