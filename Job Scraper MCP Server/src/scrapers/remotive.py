"""
Remotive scraper — free public API, no key required.

Remote-only source. Used exclusively in Mode 3 (remote jobs).
candidate_required_location in the response indicates which regions the job accepts.
"""
from __future__ import annotations

import logging

import httpx

from src.schema import norm

log = logging.getLogger(__name__)

_URL = "https://remotive.com/api/remote-jobs"


async def fetch(search_term: str, limit: int = 200) -> list[dict]:
    """Fetch remote jobs matching search_term from the Remotive public API."""
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(_URL, params={"search": search_term, "limit": limit})
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        log.warning("remotive error (term=%r): %s", search_term, exc)
        return [{"_error": f"remotive: {exc}"}]

    return [
        norm(
            source="remotive",
            title=r.get("title"),
            company=r.get("company_name"),
            job_link=r.get("url"),
            apply_link=r.get("url"),
            company_link=r.get("company_logo", ""),
            description=r.get("description"),
            location=r.get("candidate_required_location"),
            date_posted=r.get("publication_date"),
            job_type=r.get("job_type"),
            is_remote=True,
            salary=r.get("salary"),
        )
        for r in data.get("jobs", [])[:limit]
    ]
