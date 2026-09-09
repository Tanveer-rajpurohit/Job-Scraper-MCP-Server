"""
Google Drive handoff uploader for the Job Scraper MCP server.

Posts complete scraped datasets to a Google Apps Script Web App (Option A:
zero GCP setup, zero service accounts) which writes them as JSON files into
the "gemini spark data" Drive folder. Gemini Spark can then read those files
natively with its Google Drive tool instead of ingesting megabyte-scale MCP
tool responses.

Design notes:
- If GOOGLE_DRIVE_WEBHOOK_URL is not configured, upload is skipped gracefully
  and the local data/modeX.json files remain the single source of truth.
- Upload failures never fail the scraper tool run; they are reported in the
  tool response as a non-fatal status so Gemini Spark can still use
  get_saved_jobs against the local dataset.
- follow_redirects=True is mandatory: Apps Script Web Apps answer POSTs with
  a 302 to script.googleusercontent.com, which httpx does not follow by default.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Any

try:
    import httpx
except ImportError:
    httpx = None

from src.config import DRIVE_FOLDER_NAME, GOOGLE_DRIVE_WEBHOOK_URL

log = logging.getLogger(__name__)

_UPLOAD_TIMEOUT_SECONDS = 60


async def upload_to_drive(mode_name: str, jobs: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Uploads the complete job dataset for a mode to the configured Drive folder.

    Returns a status dictionary shaped for direct inclusion in the MCP tool
    response: {"status", "file_name", "drive_link"} on success,
    {"status": "skipped"|"failed", "reason"} otherwise. Never raises.
    """
    if not GOOGLE_DRIVE_WEBHOOK_URL:
        return {
            "status": "skipped",
            "reason": "GOOGLE_DRIVE_WEBHOOK_URL not configured; dataset saved locally only.",
        }

    clean_mode = mode_name.lower().replace(".json", "")
    file_name = f"{clean_mode}.json"
    content = json.dumps(
        {
            "mode": clean_mode,
            "generated_at": datetime.now().isoformat(),
            "total_jobs": len(jobs),
            "jobs": jobs,
        },
        ensure_ascii=False,
    )
    request_payload = {
        "file_name": file_name,
        "folder": DRIVE_FOLDER_NAME,
        "content": content,
    }

    try:
        if httpx is not None:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                resp = await client.post(
                    GOOGLE_DRIVE_WEBHOOK_URL,
                    json=request_payload,
                    timeout=_UPLOAD_TIMEOUT_SECONDS,
                )
                resp.raise_for_status()
                result = resp.json()
        else:
            import urllib.request

            def _sync_post() -> dict[str, Any]:
                data_bytes = json.dumps(request_payload).encode("utf-8")
                req = urllib.request.Request(
                    GOOGLE_DRIVE_WEBHOOK_URL,
                    data=data_bytes,
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=_UPLOAD_TIMEOUT_SECONDS) as r:
                    return json.loads(r.read().decode("utf-8"))

            result = await asyncio.to_thread(_sync_post)
    except Exception as exc:
        log.warning("Drive upload failed for %s: %s", mode_name, exc)
        return {
            "status": "failed",
            "reason": str(exc),
            "note": "Dataset is still available locally; use get_saved_jobs.",
        }

    return {
        "status": "success",
        "file_name": file_name,
        "drive_link": str(result.get("drive_link", "")),
        "file_id": str(result.get("file_id", "")),
    }
