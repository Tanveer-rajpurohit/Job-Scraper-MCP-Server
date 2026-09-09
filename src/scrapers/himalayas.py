"""
Himalayas scraper module for remote tech engineering opportunities.

Fetches remote listings from the Himalayas public REST API with zero API keys.
Extracts direct application links, seniority classifications, and salary ranges.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from src.schema import norm

log = logging.getLogger(__name__)

_URL = "https://himalayas.app/jobs/api"


async def fetch(search_term: str, limit: int = 50) -> list[dict[str, Any]]:
    """
    Retrieves remote developer positions from Himalayas matching the given keyword.
    """
    params = {"search": search_term, "limit": limit}
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        log.warning("himalayas error (term=%r): %s", search_term, exc)
        return [{"_error": f"himalayas: {exc}"}]

    out = []
    for r in data.get("jobs", [])[:limit]:
        min_sal = r.get("minSalary")
        max_sal = r.get("maxSalary")
        currency = r.get("currency", "USD")
        salary = f"{currency} {min_sal}-{max_sal}" if (min_sal or max_sal) else ""

        locations = r.get("locationRestrictions", [])
        loc_str = ", ".join(locations) if locations else "Worldwide Remote"

        out.append(
            norm(
                source="himalayas",
                title=r.get("title"),
                company=r.get("companyName"),
                job_link=r.get("applicationLink") or r.get("guid", ""),
                apply_link=r.get("applicationLink") or r.get("guid", ""),
                company_link=f"https://himalayas.app/companies/{r.get('companySlug', '')}",
                description=r.get("description") or r.get("excerpt", ""),
                location=loc_str,
                date_posted=r.get("pubDate"),
                job_type=r.get("employmentType", "fulltime"),
                is_remote=True,
                salary=salary,
            )
        )
    return out
