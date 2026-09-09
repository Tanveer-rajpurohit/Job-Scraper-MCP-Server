"""
Mode 3: Remote engineering jobs sweep.

Queries JobSpy (is_remote=True), Adzuna India, Remotive, Himalayas, and Arbeitnow
for remote software engineering positions open to Indian candidates.

Tailored to 2027 graduate opportunities (Internships, PPO, Freshers, 0-2 years Junior/SDE-1).
Saves the full dataset to data/mode3.json and returns the filtered, HMAC-deduplicated
jobs list directly in the MCP response for Gemini Spark.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from src.config import HOURS_OLD
from src.merge import merge
from src.scrapers import adzuna, arbeitnow, himalayas, jobspy, remotive
from src.storage import save_mode_jobs

log = logging.getLogger(__name__)

MODE3_TERMS = [
    "Remote SDE Intern",
    "Remote Software Intern",
    "Remote Junior Developer",
    "Remote Backend Developer",
    "Remote Full Stack Developer",
    "Remote Frontend Developer",
    "Remote DevOps",
    "Remote AI Engineer",
    "Remote Go Developer",
]


async def run_mode3() -> dict[str, Any]:
    """
    Executes searches across 5 sources for remote roles.
    Deduplicates by HMAC signature, filters out senior positions, writes data/mode3.json,
    and returns the clean jobs array directly to Gemini Spark.
    """
    log.info("Mode 3 — remote: querying %d keywords across 5 remote sources", len(MODE3_TERMS))

    tasks = []
    for term in MODE3_TERMS:
        tasks.append(jobspy.fetch(term, location="India", hours_old=HOURS_OLD, is_remote=True))
        tasks.append(adzuna.fetch(term, location=""))
        tasks.append(remotive.fetch(term))
        tasks.append(himalayas.fetch(term, limit=20))
        tasks.append(arbeitnow.fetch(term, limit=20))

    all_results = await asyncio.gather(*tasks)
    jobs, errors = merge(*all_results)

    storage_info = save_mode_jobs("mode3", jobs)
    log.info("Mode 3 finished: %d remote graduate-suitable jobs saved to %s", len(jobs), storage_info["file_name"])

    return {
        "mode": "mode3",
        "total_jobs": len(jobs),
        "file_saved": storage_info["file_name"],
        "jobs": jobs,
        "errors": errors,
    }


def register(mcp: Any) -> None:
    """
    Registers the scrape_jobs_remote tool on the FastMCP server instance.
    """

    @mcp.tool()
    async def scrape_jobs_remote(dummy: str = "") -> dict[str, Any]:
        """
        Mode 3 — Remote jobs open to India-based candidates.

        Queries 9 remote keywords across JobSpy, Adzuna India, Remotive, Himalayas,
        and Arbeitnow for fresh postings (last 3-4 days).
        Automatically filters out senior/lead/architect roles and demands of 3+ years experience.

        Saves data/mode3.json and returns the full list of suitable jobs in the response.

        Args:
            dummy: unused placeholder — pass "" or omit.

        Returns:
            Dictionary containing mode name, total_jobs count, file_saved confirmation,
            and the full list of normalized, graduate-suitable job objects.
        """
        return await run_mode3()
