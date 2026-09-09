"""
Jooble scraper module for Indian jobs aggregation.

Queries the official Jooble REST API with graceful quota protection.
If the daily quota is exhausted, returns an empty list without halting
or disrupting other parallel scraper sources.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from src.config import JOOBLE_API_KEY
from src.schema import norm

log = logging.getLogger(__name__)

_BASE_URL = "https://jooble.org/api"
_SEMAPHORE = asyncio.Semaphore(2)


async def _fetch_page(
    client: httpx.AsyncClient,
    search_term: str,
    location: str,
    page: int = 1,
) -> list[dict[str, Any]]:
    """
    Executes a single page query against the Jooble API with quota protection.
    """
    if not JOOBLE_API_KEY:
        return []

    url = f"{_BASE_URL}/{JOOBLE_API_KEY}"
    payload = {
        "keywords": search_term,
        "location": location or "India",
        "page": page,
        "result_on_page": 50,
    }

    async with _SEMAPHORE:
        await asyncio.sleep(0.1)
        try:
            resp = await client.post(url, json=payload, timeout=20)
            if resp.status_code in (401, 402, 403, 429):
                log.warning("Jooble API quota reached or key invalid (status %d)", resp.status_code)
                return []
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            log.warning("Jooble error (term=%r page=%d): %s", search_term, page, exc)
            return []

    out = []
    for r in data.get("jobs", []):
        out.append(
            norm(
                source="jooble",
                title=r.get("title"),
                company=r.get("company"),
                job_link=r.get("link"),
                apply_link=r.get("link"),
                company_link="",
                description=r.get("snippet"),
                location=r.get("location") or location or "India",
                date_posted=r.get("updated"),
                job_type=r.get("type", "fulltime"),
                is_remote=None,
                salary=r.get("salary", ""),
            )
        )
    return out


async def fetch(search_term: str, location: str = "India") -> list[dict[str, Any]]:
    """
    Fetches listings from Jooble India.
    Retrieves page 1, and only proceeds to page 2 if page 1 returns 50 results.
    """
    async with httpx.AsyncClient() as client:
        page1 = await _fetch_page(client, search_term, location, page=1)
        if len(page1) >= 50:
            page2 = await _fetch_page(client, search_term, location, page=2)
            return page1 + page2
        return page1
