"""
Mode 3: Remote engineering jobs sweep.

Queries JobSpy (is_remote=True), Adzuna India, Remotive, Himalayas, and Arbeitnow
for remote software engineering positions open to Indian candidates.

Tailored to 2027 graduate opportunities (Internships, PPO, Freshers, 0-2 years Junior/SDE-1).
Saves the full dataset to data/mode3.json (atomic write), uploads it to Google Drive,
and returns a lightweight summary with a top preview for Gemini Spark.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from src.config import HOURS_OLD
from src.drive import upload_to_drive
from src.merge import make_response, merge
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
    Deduplicates by cross-board HMAC signature, filters out senior positions,
    atomically writes data/mode3.json, uploads the dataset to Google Drive,
    and returns a lightweight summary with a top preview to Gemini Spark.
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
    drive_info = await upload_to_drive("mode3", jobs)
    log.info(
        "Mode 3 finished: %d remote graduate-suitable jobs saved to %s (drive: %s)",
        len(jobs),
        storage_info["file_name"],
        drive_info["status"],
    )

    return make_response("mode3", jobs, errors, storage_info, drive_info)


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

        Saves data/mode3.json, uploads the full dataset to Google Drive, and returns
        a lightweight summary: total count, Drive link, and a top preview of jobs
        with apply links (no full descriptions).

        Args:
            dummy: unused placeholder — pass "" or omit.

        Returns:
            Dictionary containing mode name, total_jobs count, file_saved confirmation,
            Google Drive upload status, and preview_jobs (top matches with apply links).
            Use get_saved_jobs(mode="mode3", offset=N) for full descriptions in batches.
        """
        return await run_mode3()
