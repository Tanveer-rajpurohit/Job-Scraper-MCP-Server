"""
Standalone test script for verifying scrapers across multiple keywords.

Executes a sample query across multiple distinct graduate keywords:
- SDE Intern
- Junior Backend Developer
- Go Developer
Demonstrates rich description enrichment and verifies graduate filtering.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from src.merge import merge
from src.scrapers import adzuna, arbeitnow, himalayas, jobspy, jooble, remotive
from src.storage import save_mode_jobs


async def run_test() -> None:
    """
    Runs live queries across 3 representative graduate keywords and tests enrichment.
    """
    test_keywords = ["SDE Intern", "Junior Backend Developer", "Go Developer"]
    print(f"Starting test scrape across {len(test_keywords)} distinct keywords...")

    all_gathered_jobs = []

    for kw in test_keywords:
        print(f"Querying keyword: '{kw}' across 6 sources...")
        tasks = [
            adzuna.fetch(kw, location="India"),
            jooble.fetch(kw, location="India"),
            remotive.fetch(kw, limit=3),
            himalayas.fetch(kw, limit=3),
            arbeitnow.fetch(kw, limit=3),
            jobspy.fetch(kw, location="India", hours_old=96, results_wanted=3),
        ]
        results = await asyncio.gather(*tasks)
        jobs, errors = merge(*results)
        print(f"  -> '{kw}': {len(jobs)} graduate-suitable unique jobs found")
        all_gathered_jobs.extend(jobs)

    final_unique_jobs, _ = merge(all_gathered_jobs)
    print(f"\nTotal aggregated unique jobs across keywords: {len(final_unique_jobs)}")

    storage_info = save_mode_jobs("mode1", final_unique_jobs)
    saved_file = Path(storage_info["file_path"])
    print(f"Successfully wrote data to: {saved_file.resolve()}")

    if final_unique_jobs:
        sample = final_unique_jobs[0]
        print("\n--- SAMPLE ENRICHED JOB OUTPUT FOR GEMINI SPARK ---")
        print(json.dumps(sample, indent=2, ensure_ascii=False))
        print("---------------------------------------------------")

        print("\nVerification checks:")
        print(f"1. Has deterministic HMAC ID: {bool(sample.get('id'))} ({sample.get('id')})")
        print(f"2. Has job link: {bool(sample.get('job_link'))}")
        print(f"3. Has apply link: {bool(sample.get('apply_link'))}")
        print(f"4. Description length: {len(sample.get('description', ''))} chars (max 2800)")
        print(f"5. Senior filter check: '{'senior' not in sample.get('title', '').lower()}'")
        print(f"6. Structured header included: {'Position:' in sample.get('description', '')}")

    print("\nTest completed successfully.")


if __name__ == "__main__":
    asyncio.run(run_test())
