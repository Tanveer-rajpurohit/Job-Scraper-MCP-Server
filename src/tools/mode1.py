"""
Mode 1: Pan-India SDE and engineering roles sweep.

Queries JobSpy, Adzuna India, Jooble, Remotive, Himalayas, and Arbeitnow using focused
keywords aligned with Tanveer's 5 resume profiles (Go Backend, SDE General, DevOps,
Creative Frontend, GenAI) for 2027 graduate opportunities.

Saves the complete dataset to data/mode1.json and returns the filtered,
HMAC-deduplicated jobs list directly in the MCP response for Gemini Spark.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from src.config import HOURS_OLD
from src.merge import merge
from src.scrapers import adzuna, arbeitnow, himalayas, jobspy, jooble, remotive
from src.storage import save_mode_jobs

log = logging.getLogger(__name__)

MODE1_TERMS = [
    "SDE Intern",
    "Software Engineer Intern",
    "Graduate Engineer Trainee",
    "SDE 1",
    "Junior Software Engineer",
    "Junior Backend Developer",
    "Go Developer",
    "Node.js Developer",
    "Full Stack Developer",
    "Frontend Developer",
    "React Developer",
    "DevOps Engineer",
    "Python AI Developer",
]


async def run_mode1() -> dict[str, Any]:
    """
    Executes searches across 6 sources for 2027 graduate roles.
    Deduplicates by HMAC signature, filters out senior positions, writes data/mode1.json,
    and returns the clean jobs array directly to Gemini Spark.
    """
    log.info("Mode 1 — india_all: querying %d keywords across 6 sources", len(MODE1_TERMS))

    tasks = []
    for term in MODE1_TERMS:
        tasks.append(jobspy.fetch(term, location="India", hours_old=HOURS_OLD, is_remote=False))
        tasks.append(adzuna.fetch(term, location="India"))
        tasks.append(jooble.fetch(term, location="India"))
        tasks.append(remotive.fetch(term))
        tasks.append(himalayas.fetch(term, limit=15))
        tasks.append(arbeitnow.fetch(term, limit=15))

    all_results = await asyncio.gather(*tasks)
    jobs, errors = merge(*all_results)

    storage_info = save_mode_jobs("mode1", jobs)
    log.info("Mode 1 finished: %d graduate-suitable jobs saved to %s", len(jobs), storage_info["file_name"])

    return {
        "mode": "mode1",
        "total_jobs": len(jobs),
        "file_saved": storage_info["file_name"],
        "jobs": jobs,
        "errors": errors,
    }


def register(mcp: Any) -> None:
    """
    Registers the scrape_jobs_india_all tool on the FastMCP server instance.
    """

    @mcp.tool()
    async def scrape_jobs_india_all(dummy: str = "") -> dict[str, Any]:
        """
        Mode 1 — Broad India job sweep for 2027 graduates and junior engineers.

        Searches 13 targeted engineering keywords across 6 platforms: JobSpy
        (LinkedIn, Indeed, Google), Adzuna India, Jooble India, Remotive, Himalayas, and Arbeitnow.
        Automatically filters out senior/lead/architect roles and demands of 3+ years experience.

        Saves data/mode1.json and returns the full list of suitable jobs in the response.

        Args:
            dummy: unused placeholder — pass "" or omit.

        Returns:
            Dictionary containing mode name, total_jobs count, file_saved confirmation,
            and the full list of normalized, graduate-suitable job objects.
        """
        return await run_mode1()
