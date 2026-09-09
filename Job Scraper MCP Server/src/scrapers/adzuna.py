"""
Adzuna scraper module with rate-limiting semaphore and smart pagination.

Queries the official Adzuna India API with controlled concurrency to prevent
rate limiting. Only requests subsequent pages if earlier pages are fully populated.
Gracefully handles quota limits by returning an empty list rather than blocking.
"""
from __future__ import annotations

import asyncio
import logging

import httpx

from src.config import ADZUNA_APP_ID, ADZUNA_APP_KEY, ADZUNA_COUNTRY, HOURS_OLD
from src.schema import norm

log = logging.getLogger(__name__)

_BASE = "https://api.adzuna.com/v1/api/jobs"
_SEMAPHORE = asyncio.Semaphore(3)


async def _page(
    client: httpx.AsyncClient,
    search_term: str,
    location: str,
    page: int,
    per_page: int = 50,
) -> list[dict]:
    """
    Fetches a single page of results from Adzuna under concurrency semaphore control.
    """
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        return []

    params: dict = {
        "app_id": ADZUNA_APP_ID,
        "app_key": ADZUNA_APP_KEY,
        "results_per_page": per_page,
        "what": search_term,
        "content-type": "application/json",
        "max_days_old": max(HOURS_OLD // 24, 1),
    }
    if location:
        params["where"] = location

    url = f"{_BASE}/{ADZUNA_COUNTRY}/search/{page}"

    async with _SEMAPHORE:
        await asyncio.sleep(0.15)
        try:
            resp = await client.get(url, params=params, timeout=25)
            if resp.status_code == 429:
                await asyncio.sleep(1.0)
                resp = await client.get(url, params=params, timeout=25)
            if resp.status_code in (401, 402, 403, 429):
                log.warning("Adzuna API quota reached or key invalid (status %d)", resp.status_code)
                return []
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            log.warning("adzuna error (term=%r page=%d): %s", search_term, page, exc)
            return []

    out = []
    for r in data.get("results", []):
        company = (r.get("company") or {}).get("display_name", "")
        loc = (r.get("location") or {}).get("display_name", "")
        sal_min = r.get("salary_min")
        sal_max = r.get("salary_max")
        salary = f"INR {sal_min}-{sal_max}" if (sal_min or sal_max) else ""
        out.append(norm(
            source="adzuna",
            title=r.get("title"),
            company=company,
            job_link=r.get("redirect_url"),
            apply_link=r.get("redirect_url"),
            company_link="",
            description=r.get("description"),
            location=loc,
            date_posted=r.get("created"),
            job_type=r.get("contract_time", ""),
            is_remote=None,
            salary=salary,
        ))
    return out


async def fetch(search_term: str, location: str = "") -> list[dict]:
    """
    Fetches job listings from Adzuna India.
    Only proceeds to fetch page 2 if page 1 returns a complete batch of 50 results.
    """
    async with httpx.AsyncClient() as client:
        page1 = await _page(client, search_term, location, page=1, per_page=50)
        if len(page1) >= 50:
            page2 = await _page(client, search_term, location, page=2, per_page=50)
            return page1 + page2
        return page1
