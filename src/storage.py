"""
Storage management for Mode 1, Mode 2, and Mode 3 JSON files.

Maintains three dedicated files in the data directory:
- data/mode1.json (Pan-India SDE & fresher sweep)
- data/mode2.json (Location-focused sweep)
- data/mode3.json (Remote jobs sweep)

Each tool run overwrites its respective JSON file with fresh results,
preventing stale accumulation across runs while protecting MCP message limits.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

DATA_DIR = Path("data")


def get_mode_filepath(mode_name: str) -> Path:
    """
    Returns the resolved Path for a given mode file.
    Valid mode names are mode1, mode2, and mode3.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    clean_name = mode_name.lower().replace(".json", "")
    return DATA_DIR / f"{clean_name}.json"


def save_mode_jobs(mode_name: str, jobs: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Overwrites the corresponding mode JSON file with freshly scraped jobs.
    Saves complete job payloads including full descriptions, apply links, and hashes.

    Writes to a temporary file first, then atomically replaces the target via
    Path.replace() (os.rename semantics) so an interrupted process can never
    leave a truncated or half-written mode file behind.
    """
    filepath = get_mode_filepath(mode_name)
    temp_filepath = filepath.with_suffix(".tmp.json")

    payload = {
        "mode": mode_name,
        "updated_at": datetime.now().isoformat(),
        "total_jobs": len(jobs),
        "jobs": jobs,
    }

    with temp_filepath.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    temp_filepath.replace(filepath)

    return {
        "file_path": str(filepath.resolve()),
        "file_name": filepath.name,
        "total_saved": len(jobs),
        "updated_at": payload["updated_at"],
    }


def read_mode_jobs(mode_name: str, offset: int = 0, limit: int = 50) -> dict[str, Any]:
    """
    Reads a slice of jobs from the designated mode file.
    Enables Gemini Spark to fetch jobs in safe batches of 20 to 50 items.
    """
    filepath = get_mode_filepath(mode_name)
    if not filepath.exists():
        return {
            "mode": mode_name,
            "total_jobs": 0,
            "offset": offset,
            "limit": limit,
            "jobs": [],
            "has_more": False,
            "error": f"File {filepath.name} does not exist yet. Run the scraper first.",
        }

    try:
        with filepath.open("r", encoding="utf-8") as f:
            data = json.load(f)
            all_jobs = data.get("jobs", [])
            total = len(all_jobs)
            slice_jobs = all_jobs[offset : offset + limit]
            return {
                "mode": mode_name,
                "total_jobs": total,
                "offset": offset,
                "limit": limit,
                "returned_count": len(slice_jobs),
                "has_more": (offset + limit) < total,
                "jobs": slice_jobs,
            }
    except Exception as exc:
        return {
            "mode": mode_name,
            "total_jobs": 0,
            "offset": offset,
            "limit": limit,
            "jobs": [],
            "has_more": False,
            "error": str(exc),
        }
