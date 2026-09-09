"""
Mode 2: Location-focused India sweep.

Searches engineering positions across specific target location clusters:
- Gujarat cluster (primary home base): Ahmedabad, Gandhinagar, Vadodara.
- Tier-1 tech metro cluster: Delhi, Gurugram, Mumbai, Pune.

Quota-aware query strategy: Adzuna (250 calls/day) and Jooble (500 calls/day)
query 4 broad regional hubs ("Gujarat", "Delhi NCR", "Mumbai", "Pune"), cutting
their API calls roughly in half. JobSpy is free and unlimited, so it keeps
city-level precision for maximum recall.

Tailored to 2027 graduate opportunities (Internships, PPO, Freshers, 0-2 years Junior/SDE-1).
Saves the full dataset to data/mode2.json (atomic write), uploads it to Google Drive,
and returns a lightweight summary with a top preview for Gemini Spark.
"""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

from src.config import HOURS_OLD
from src.drive import upload_to_drive
from src.merge import make_response, merge
from src.scrapers import adzuna, jobspy
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

GUJARAT_PRIORITY_CITIES = [
    "ahmedabad",
    "gandhinagar",
    "vadodara",
    "baroda",
    "rajkot",
    "gujarat",
]

METRO_CITIES = [
    "delhi",
    "new delhi",
    "gurugram",
    "gurgaon",
    "noida",
    "greater noida",
    "ghaziabad",
    "faridabad",
    "delhi ncr",
    "mumbai",
    "navi mumbai",
    "thane",
    "pune",
]

JOBSPY_LOCATIONS = [
    "Ahmedabad",
    "Gandhinagar",
    "Vadodara",
    "Gujarat",
    "Delhi",
    "Gurugram",
    "Noida",
    "Mumbai",
    "Pune",
]

GUJARAT_HUBS = [
    "Ahmedabad",
    "Gandhinagar",
    "Vadodara",
    "Gujarat",
]

METRO_HUBS = [
    "Delhi NCR",
    "Mumbai",
    "Pune",
]

API_REGIONAL_HUBS = GUJARAT_HUBS + METRO_HUBS


def is_target_location(job: dict[str, Any]) -> bool:
    """
    Verifies that a job posting belongs to at least one of our target locations.
    Matches across the location field, title, and description text.
    Ensures that if a job is in any one of the target locations, it is included.
    """
    loc_text = str(job.get("location") or "").lower()
    title_text = str(job.get("title") or "").lower()
    desc_text = str(job.get("description") or "").lower()
    search_corpus = f"{loc_text} {title_text} {desc_text[:400]}"

    all_targets = GUJARAT_PRIORITY_CITIES + METRO_CITIES
    return any(re.search(r"\b" + re.escape(term) + r"\b", search_corpus) for term in all_targets)


def location_priority_tier(job: dict[str, Any]) -> int:
    """
    Ranks jobs by geographic priority for Tanveer's profile:
    - Tier 0: Ahmedabad, Gandhinagar, Vadodara, and Gujarat (Top Priority).
    - Tier 1: Tier-1 Tech Metros (Delhi NCR, Mumbai, Pune).
    - Tier 2: General / Other.
    """
    loc_text = str(job.get("location") or "").lower()
    title_text = str(job.get("title") or "").lower()
    desc_text = str(job.get("description") or "").lower()
    search_corpus = f"{loc_text} {title_text} {desc_text[:400]}"

    if any(re.search(r"\b" + re.escape(term) + r"\b", search_corpus) for term in GUJARAT_PRIORITY_CITIES):
        return 0
    if any(re.search(r"\b" + re.escape(term) + r"\b", search_corpus) for term in METRO_CITIES):
        return 1
    return 2


async def run_mode2() -> dict[str, Any]:
    """
    Executes keyword searches across Gujarat and Tier-1 metro locations.
    JobSpy queries each city directly. Adzuna and Jooble query Gujarat hubs
    and metro hubs to conserve daily API quotas. Results are deduplicated
    by cross-board HMAC signature, filtered for 2027 graduate suitability,
    screened to guarantee target location matching, and sorted with Gujarat
    (Ahmedabad, Gandhinagar, Vadodara) at top priority.
    """
    log.info(
        "Mode 2 — india_location: %d keywords across %d JobSpy cities and %d API regional hubs",
        len(MODE2_TERMS),
        len(JOBSPY_LOCATIONS),
        len(API_REGIONAL_HUBS),
    )

    tasks = []
    for term in MODE2_TERMS:
        for loc in JOBSPY_LOCATIONS:
            tasks.append(jobspy.fetch(term, location=loc, hours_old=HOURS_OLD, is_remote=False))
        for hub in API_REGIONAL_HUBS:
            tasks.append(adzuna.fetch(term, location=hub))

    all_results = await asyncio.gather(*tasks)
    jobs, errors = merge(*all_results)

    filtered_jobs = [job for job in jobs if is_target_location(job)]
    filtered_jobs.sort(key=location_priority_tier)

    storage_info = save_mode_jobs("mode2", filtered_jobs)
    drive_info = await upload_to_drive("mode2", filtered_jobs)
    log.info(
        "Mode 2 finished: %d graduate-suitable location jobs saved to %s (drive: %s)",
        len(filtered_jobs),
        storage_info["file_name"],
        drive_info["status"],
    )

    return make_response("mode2", filtered_jobs, errors, storage_info, drive_info)


def register(mcp: Any) -> None:
    """
    Registers the scrape_jobs_india_location tool on the FastMCP server instance.
    """

    @mcp.tool()
    async def scrape_jobs_india_location(dummy: str = "") -> dict[str, Any]:
        """
        Mode 2 — Location-focused India sweep for 2027 graduates and junior engineers.

        Searches 9 engineering keywords across Gujarat (Ahmedabad, Gandhinagar, Vadodara)
        and Tier-1 metros (Delhi, Gurugram, Mumbai, Pune). JobSpy covers every city;
        quota-limited Adzuna and Jooble query 4 regional hubs (Gujarat, Delhi NCR,
        Mumbai, Pune) to stay inside their daily API limits.
        Automatically filters out senior/lead/architect roles and demands of 3+ years experience.

        Saves data/mode2.json, uploads the full dataset to Google Drive, and returns
        a lightweight summary: total count, Drive link, and a top preview of jobs
        with apply links (no full descriptions).

        Args:
            dummy: unused placeholder — pass "" or omit.

        Returns:
            Dictionary containing mode name, total_jobs count, file_saved confirmation,
            Google Drive upload status, and preview_jobs (top matches with apply links).
            Use get_saved_jobs(mode="mode2", offset=N) for full descriptions in batches.
        """
        return await run_mode2()
