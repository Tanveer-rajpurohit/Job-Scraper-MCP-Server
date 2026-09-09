"""
Arbeitnow scraper module for tech positions and remote developer opportunities.

Queries the Arbeitnow public JSON API with zero authentication requirements.
Normalizes postings and maps remote employment attributes into canonical job records.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import httpx

from src.schema import norm

log = logging.getLogger(__name__)

_URL = "https://www.arbeitnow.com/api/job-board-api"


async def fetch(search_term: str, limit: int = 50) -> list[dict[str, Any]]:
    """
    Fetches job listings from Arbeitnow matching the search term across titles and tags.
    """
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(_URL)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        log.warning("arbeitnow error (term=%r): %s", search_term, exc)
        return [{"_error": f"arbeitnow: {exc}"}]

    clean_term = search_term.lower().strip()
    matching_jobs = []

    for r in data.get("data", []):
        title = str(r.get("title", ""))
        desc = str(r.get("description", ""))
        tags = " ".join(r.get("tags", []))

        content_blob = f"{title} {desc} {tags}".lower()
        if clean_term in content_blob or not clean_term:
            created_ts = r.get("created_at")
            date_str = ""
            if created_ts:
                try:
                    date_str = datetime.fromtimestamp(created_ts).isoformat()
                except Exception:
                    date_str = str(created_ts)

            matching_jobs.append(
                norm(
                    source="arbeitnow",
                    title=title,
                    company=r.get("company_name"),
                    job_link=r.get("url"),
                    apply_link=r.get("url"),
                    company_link="",
                    description=desc,
                    location=r.get("location", "Remote"),
                    date_posted=date_str,
                    job_type=", ".join(r.get("job_types", [])) or "fulltime",
                    is_remote=bool(r.get("remote")),
                    salary="",
                )
            )

        if len(matching_jobs) >= limit:
            break

    return matching_jobs
