# sandbox_api/screens.py
import subprocess, io
from fastapi import HTTPException
from fastapi.responses import Response
from .settings import settings

def screenshot_png_response() -> Response:
    try:
        p = subprocess.run(settings.SCREENSHOT_CMD, shell=True, check=True, stdout=subprocess.PIPE)
        return Response(content=p.stdout, media_type="image/png")
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"screenshot failed: {e}")
