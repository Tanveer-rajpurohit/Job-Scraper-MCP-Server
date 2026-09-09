"""
Merge and filter module for combining and deduplicating scraper results.

Performs deterministic deduplication using HMAC job identifiers and filters
out positions unsuitable for a 2027 graduate candidate (0-2 years experience).
"""
from __future__ import annotations

from typing import Any

from src.filter import filter_suitable_jobs


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


def make_response(jobs: list[dict[str, Any]], errors: list[str], mode: str) -> dict[str, Any]:
    """
    Wraps the final jobs collection in the standard MCP tool response envelope.
    """
    return {"mode": mode, "total_jobs": len(jobs), "jobs": jobs, "errors": errors}
