# sandbox_api/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    CONTROL_PLANE_URL: str | None = None      # e.g., https://paladin-mvp-backend.onrender.com
    CONTROL_PLANE_TOKEN: str | None = None    # bearer for POST /api/findings
    ALLOW_EXEC: int = 1                       # 0/1 to enable /execute
    SCREENSHOT_CMD: str = "xwd -root -silent | convert xwd:- png:-"
    TIMEOUT_DEFAULT: int = 120

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
