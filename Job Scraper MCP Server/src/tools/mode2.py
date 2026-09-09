"""
Mode 2: Location-focused India sweep.

Searches engineering positions across specific target location clusters:
- Gujarat cluster (primary home base): Ahmedabad, Gandhinagar, Vadodara.
- Tier-1 tech metro cluster: Gurugram, Delhi, Mumbai, Pune.

Queries JobSpy, Adzuna India, and Jooble with location parameters.
Tailored to 2027 graduate opportunities (Internships, PPO, Freshers, 0-2 years Junior/SDE-1).
Saves the full dataset to data/mode2.json and returns the filtered, HMAC-deduplicated
jobs list directly in the MCP response for Gemini Spark.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from src.config import HOURS_OLD
from src.merge import merge
from src.scrapers import adzuna, jobspy, jooble
from src.storage import save_mode_jobs

log = logging.getLogger(__name__)

MODE2_TERMS = [
    "SDE Intern",
    "Software Engineer Intern",
    "SDE 1",
    "Junior Software Engineer",
    "Backend Developer",
    "Full Stack Developer",
    "Frontend Developer",
    "Go Developer",
    "DevOps",
]

GUJARAT_LOCATIONS = ["Ahmedabad", "Gandhinagar", "Vadodara"]
METRO_LOCATIONS = ["Gurugram", "Delhi", "Mumbai", "Pune"]


async def run_mode2() -> dict[str, Any]:
    """
    Executes separate keyword searches across Gujarat and top Tier-1 metro locations.
    Queries JobSpy, Adzuna, and Jooble with location filtering.
    Deduplicates results by HMAC signature, filters out senior positions, writes data/mode2.json,
    and returns the clean jobs array directly to Gemini Spark.
    """
    all_locations = GUJARAT_LOCATIONS + METRO_LOCATIONS
    log.info(
        "Mode 2 — india_location: querying %d keywords across %d locations",
        len(MODE2_TERMS),
        len(all_locations),
    )

    tasks = []
    for term in MODE2_TERMS:
        for loc in all_locations:
            tasks.append(jobspy.fetch(term, location=loc, hours_old=HOURS_OLD, is_remote=False))
            tasks.append(adzuna.fetch(term, location=loc))
            tasks.append(jooble.fetch(term, location=loc))

    all_results = await asyncio.gather(*tasks)
    jobs, errors = merge(*all_results)

    storage_info = save_mode_jobs("mode2", jobs)
    log.info("Mode 2 finished: %d graduate-suitable jobs saved to %s", len(jobs), storage_info["file_name"])

    return {
        "mode": "mode2",
        "total_jobs": len(jobs),
        "file_saved": storage_info["file_name"],
        "jobs": jobs,
        "errors": errors,
    }


def register(mcp: Any) -> None:
    """
    Registers the scrape_jobs_india_location tool on the FastMCP server instance.
    """

    @mcp.tool()
    async def scrape_jobs_india_location(dummy: str = "") -> dict[str, Any]:
        """
        Mode 2 — Location-focused India sweep for 2027 graduates and junior engineers.

        Searches 9 engineering keywords across Gujarat (Ahmedabad, Gandhinagar, Vadodara)
        and Tier-1 metros (Gurugram, Delhi, Mumbai, Pune) via JobSpy, Adzuna, and Jooble.
        Automatically filters out senior/lead/architect roles and demands of 3+ years experience.

        Saves data/mode2.json and returns the full list of suitable jobs in the response.

        Args:
            dummy: unused placeholder — pass "" or omit.

        Returns:
            Dictionary containing mode name, total_jobs count, file_saved confirmation,
            and the full list of normalized, graduate-suitable job objects.
        """
        return await run_mode2()
