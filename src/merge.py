"""
Merge and filter module for combining and deduplicating scraper results.

Performs deterministic cross-board deduplication using HMAC job identifiers
and filters out positions unsuitable for a 2027 graduate candidate (0-2 years
experience). Also builds the lightweight MCP tool response envelope so Gemini
Spark receives summary metrics and a small preview instead of megabyte-scale
full descriptions (which saturate its context window).
"""
from __future__ import annotations

from typing import Any

from src.filter import filter_suitable_jobs

PREVIEW_FIELDS = (
    "id",
    "source",
    "title",
    "company",
    "location",
    "date_posted",
    "job_type",
    "is_remote",
    "salary",
    "apply_link",
    "job_link",
)
PREVIEW_LIMIT = 15


def merge(*source_lists: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    """
    Combines results from multiple scrapers, deduplicates by HMAC id,
    and applies candidate level filtering to discard senior positions.

    Returns:
        jobs: List of deduplicated, graduate-suitable job dictionaries.
        errors: List of non-fatal error strings from scraper runs.
    """
    seen: dict[str, dict[str, Any]] = {}
    errors: list[str] = []

    for lst in source_lists:
        for item in lst:
            if "_error" in item:
                errors.append(str(item["_error"]))
            else:
                job_id = item.get("id")
                if job_id and job_id not in seen:
                    seen[job_id] = item

    all_unique_jobs = list(seen.values())
    suitable_jobs = filter_suitable_jobs(all_unique_jobs)

    return suitable_jobs, errors


def make_response(
    mode: str,
    jobs: list[dict[str, Any]],
    errors: list[str],
    storage_info: dict[str, Any],
    drive_info: dict[str, Any],
    preview_limit: int = PREVIEW_LIMIT,
) -> dict[str, Any]:
    """
    Wraps a mode run in the standard lightweight MCP tool response envelope:
    summary metrics, top preview cards (no descriptions), and the Google Drive
    handoff status. Full records live in data/{mode}.json and Drive.
    """
    preview_jobs = [
        {field: job[field] for field in PREVIEW_FIELDS if field in job}
        for job in jobs[:preview_limit]
    ]
    drive_link = str(drive_info.get("drive_link", ""))
    return {
        "status": "success",
        "mode": mode,
        "total_jobs": len(jobs),
        "drive_link": drive_link,
        "file_saved": storage_info["file_name"],
        "drive": drive_info,
        "preview_count": len(preview_jobs),
        "preview_jobs": preview_jobs,
        "has_more": len(jobs) > preview_limit,
        "errors": errors,
        "note": (
            f"Preview shows top {len(preview_jobs)} of {len(jobs)} jobs. "
            f"Full dataset saved to {storage_info['file_name']}"
            + (" and uploaded to Google Drive." if drive_info.get("status") == "success" else ".")
            + f" Retrieve full records in token-safe batches via get_saved_jobs(mode='{mode}', offset=N, limit=20)."
        ),
    }
