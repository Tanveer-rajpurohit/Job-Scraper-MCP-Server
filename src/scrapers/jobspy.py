"""
JobSpy scraper module with asynchronous thread offloading and two-pass pagination.

Queries public guest endpoints of LinkedIn, Indeed, and Google Jobs without requiring API keys.
Controlled by a concurrency semaphore to prevent thread exhaustion.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from src.config import INDIA_SITES, RESULTS_PER_PASS
from src.schema import norm

log = logging.getLogger(__name__)

_SEMAPHORE = asyncio.Semaphore(2)


async def _single(
    search_term: str,
    location: str,
    hours_old: int,
    is_remote: bool,
    sites: list[str],
    offset: int,
    results_wanted: int,
) -> list[dict]:
    """
    Executes a single synchronous JobSpy call inside a worker thread using asyncio.to_thread.
    Transforms raw records into normalized job dictionaries under semaphore control.
    """

    def _run() -> list[dict]:
        from jobspy import scrape_jobs

        kwargs: dict[str, Any] = dict(
            site_name=sites,
            search_term=search_term,
            location=location,
            results_wanted=results_wanted,
            hours_old=hours_old,
            linkedin_fetch_description=True,
            offset=offset,
        )
        if is_remote:
            kwargs["is_remote"] = True

        df = scrape_jobs(**kwargs)
        return df.to_dict(orient="records") if df is not None and not df.empty else []

    try:
        async with _SEMAPHORE:
            records = await asyncio.to_thread(_run)
    except Exception as exc:
        log.warning("jobspy error (term=%r offset=%d): %s", search_term, offset, exc)
        return [{"_error": f"jobspy: {exc}"}]

    return [
        norm(
            source=str(r.get("site", "jobspy")),
            title=r.get("title"),
            company=r.get("company"),
            job_link=r.get("job_url"),
            apply_link=r.get("job_url_direct") or r.get("job_url"),
            company_link=r.get("company_url"),
            description=r.get("description"),
            location=r.get("location"),
            date_posted=r.get("date_posted"),
            job_type=r.get("job_type"),
            is_remote=r.get("is_remote"),
            salary=r.get("min_amount") or r.get("max_amount"),
        )
        for r in records
    ]


async def fetch(
    search_term: str,
    location: str,
    hours_old: int,
    is_remote: bool = False,
    sites: list[str] | None = None,
    results_wanted: int = RESULTS_PER_PASS,
) -> list[dict]:
    """
    Gathers jobs from JobSpy using two pagination passes (offset 0 and offset results_wanted).
    Executes both passes to reach the requested results count per term.
    """
    _sites = sites or INDIA_SITES
    pass1, pass2 = await asyncio.gather(
        _single(search_term, location, hours_old, is_remote, _sites, offset=0, results_wanted=results_wanted),
        _single(search_term, location, hours_old, is_remote, _sites, offset=results_wanted, results_wanted=results_wanted),
    )
    return pass1 + pass2
