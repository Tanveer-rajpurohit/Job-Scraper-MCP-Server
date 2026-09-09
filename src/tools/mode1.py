"""
Mode 1: Pan-India SDE and engineering roles sweep.

Queries JobSpy, Adzuna India, Jooble, Remotive, Himalayas, and Arbeitnow using focused
keywords aligned with Tanveer's 5 resume profiles (Go Backend, SDE General, DevOps,
Creative Frontend, GenAI) for 2027 graduate opportunities.

Saves the complete dataset to data/mode1.json (atomic write), uploads it to the
Google Drive "gemini spark data" folder, and returns a lightweight summary with a
top preview so Gemini Spark's context window never receives megabyte-scale payloads.
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
    Executes searches across 5 fresh sources for 2027 graduate roles.
    Deduplicates by cross-board HMAC signature, filters out senior positions and stale dates,
    atomically writes data/mode1.json, uploads the dataset to Google Drive,
    and returns a lightweight summary with a top preview to Gemini Spark.
    """
    log.info("Mode 1 — india_all: querying %d keywords across 5 fresh sources", len(MODE1_TERMS))

    tasks = []
    for term in MODE1_TERMS:
        tasks.append(jobspy.fetch(term, location="India", hours_old=HOURS_OLD, is_remote=False))
        tasks.append(adzuna.fetch(term, location="India"))
        tasks.append(remotive.fetch(term))
        tasks.append(himalayas.fetch(term, limit=15))
        tasks.append(arbeitnow.fetch(term, limit=15))

    all_results = await asyncio.gather(*tasks)
    jobs, errors = merge(*all_results)

    storage_info = save_mode_jobs("mode1", jobs)
    drive_info = await upload_to_drive("mode1", jobs)
    log.info(
        "Mode 1 finished: %d graduate-suitable jobs saved to %s (drive: %s)",
        len(jobs),
        storage_info["file_name"],
        drive_info["status"],
    )

    return make_response("mode1", jobs, errors, storage_info, drive_info)


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

        Saves data/mode1.json, uploads the full dataset to Google Drive, and returns
        a lightweight summary: total count, Drive link, and a top preview of jobs
        with apply links (no full descriptions).

        Args:
            dummy: unused placeholder — pass "" or omit.

        Returns:
            Dictionary containing mode name, total_jobs count, file_saved confirmation,
            Google Drive upload status, and preview_jobs (top matches with apply links).
            Use get_saved_jobs(mode="mode1", offset=N) for full descriptions in batches.
        """
        return await run_mode1()
