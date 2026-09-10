"""
Configuration values and environment variables for the Job Scraper MCP server.

Settings:
- ADZUNA_APP_ID: Developer app ID from developer.adzuna.com.
- ADZUNA_APP_KEY: Developer app key from developer.adzuna.com.
- ADZUNA_COUNTRY: Regional country code for Adzuna India queries ("in").
- JOOBLE_API_KEY: Authentication key for the Jooble India search API.
- HMAC_SECRET_KEY: Secret key used to sign deterministic HMAC job IDs.
- GOOGLE_DRIVE_WEBHOOK_URL: Google Apps Script Web App URL for Drive handoff.
    When empty, Drive upload is skipped gracefully and only local files are written.
- DRIVE_FOLDER_NAME: Target Drive folder for uploaded datasets (default: "gemini spark data").
- MCP_PORT: Server port for streamable HTTP transport (default: 8000).
- HOURS_OLD: 96 hours (3 to 4 days) cutoff for fresh postings.
- RESULTS_PER_PASS: 200 items requested per pagination batch.
- DESC_LIMIT: 2,800 characters limit per job description for detailed AI evaluation.
- INDIA_SITES: Supported stable job boards for JobSpy in India (JobSpy only).
"""
from __future__ import annotations

import os

from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        with env_path.open("r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    if key not in os.environ:
                        os.environ[key] = val

ADZUNA_APP_ID: str = os.environ.get("ADZUNA_APP_ID", "")
ADZUNA_APP_KEY: str = os.environ.get("ADZUNA_APP_KEY", "")
ADZUNA_COUNTRY: str = "in"

JOOBLE_API_KEY: str = os.environ.get("Jooble_API") or os.environ.get("JOOBLE_API_KEY", "")

HMAC_SECRET_KEY: str = os.environ.get("HMAC_SECRET_KEY", "job-scraper-secure-salt-2027")

GOOGLE_DRIVE_WEBHOOK_URL: str = os.environ.get("GOOGLE_DRIVE_WEBHOOK_URL", "")
DRIVE_FOLDER_NAME: str = os.environ.get("DRIVE_FOLDER_NAME", "gemini spark data")

MCP_PORT: int = int(os.environ.get("PORT") or os.environ.get("MCP_PORT", "8000"))

HOURS_OLD: int = 96
RESULTS_PER_PASS: int = 200
DESC_LIMIT: int = 2_800
INDIA_SITES: list[str] = ["indeed", "linkedin", "google"]
