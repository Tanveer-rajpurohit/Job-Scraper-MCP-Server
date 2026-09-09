"""
Candidate suitability filter for 2027 graduate profile (0-2 years experience).

Evaluates scraped job postings against experience and seniority criteria:
- Targeted: Internships, PPO opportunities, Fresher / Entry-Level (0-1 year),
  Junior, Associate (technical), SDE-1, and Member of Technical Staff (MTS-1/AMTS) roles.
- Excluded: Staff Software Engineer, Senior, Sr., Lead, Principal, Architect,
  Director, Manager, and postings explicitly demanding 3+ to 12+ years of experience.
- Excluded: Broken postings with trivial/empty descriptions (< 60 chars) lacking evaluative substance.

Evaluation order (precedence matters):
1. Senior title -> hard reject (cannot be overridden).
2. Senior experience demand (3+ years) in description -> reject, UNLESS the job
   title itself carries a strong junior signal (intern/fresher/trainee/junior/
   SDE-1). Descriptions frequently list experience ranges for multiple levels,
   so the title is the more reliable seniority signal.
3. Junior indicator anywhere (title or description) -> accept.
4. No signal at all (e.g., "Backend Engineer") -> accept by default; the senior
   rejection passes above have already screened out the known-bad cases.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from src.config import HOURS_OLD

IRRELEVANT_ROLE_PATTERNS = [
    r"\blaravel\b",
    r"\bphp\b",
    r"\bcodeigniter\b",
    r"\bsymfony\b",
    r"(?:^|[\s/])\.net\b",
    r"\bdotnet\b",
    r"\basp\.net\b",
    r"\bc#(?:\s|$|/)",
    r"\bandroid\b",
    r"\bios\b",
    r"\bflutter\b",
    r"\bswift\b",
    r"\bswiftui\b",
    r"\bkotlin\b",
    r"\breact\s+native\b",
    r"\bmobile\s+(?:developer|engineer|app)\b",
    r"\bsalesforce\b",
    r"\bsap\b",
    r"\bwordpress\b",
    r"\bmagento\b",
    r"\bshopify\b",
    r"\boracle\s+(?:cloud|hcm|erp|functional)\b",
]

SENIOR_TITLE_PATTERNS = [
    r"\bsenior\b",
    r"\bsr\b",
    r"\bsr\.",
    r"\blead\b",
    r"\bstaff\s+(?:software|engineer|developer|architect|programmer|devops|backend|frontend)\b",
    r"\bprincipal\b",
    r"\barchitect\b",
    r"\bdirector\b",
    r"\bhead of\b",
    r"\bmanager\b",
    r"\bvp\b",
    r"\bchief\b",
    r"\btech lead\b",
]

SENIOR_EXP_PATTERNS = [
    r"\b[3-9]\+\s*years?\b",
    r"\b1[0-9]\+\s*years?\b",
    r"\b[3-9]\s*to\s*[5-9]\s*years?\b",
    r"\b[5-9]\s*-\s*[8-9]\s*years?\b",
    r"\b[5-9]\.0\s*years?\b",
    r"\bminimum\s*[3-9]\s*years?\b",
    r"\bmin\s*[3-9]\s*years?\b",
    r"\bat\s*least\s*[3-9]\s*years?\b",
]

JUNIOR_POSITIVE_PATTERNS = [
    r"\bintern\b",
    r"\binternship\b",
    r"\bppo\b",
    r"\bfresher\b",
    r"\bentry\s*level\b",
    r"\bjunior\b",
    r"\bjr\b",
    r"\bjr\.",
    r"\bassociate\s+(?:software|engineer|developer|technical|sde|mts)\b",
    r"\bgraduate\b",
    r"\btrainee\b",
    r"\bsde\s*[-_]?\s*1\b",
    r"\bsde\s*[-_]?\s*i\b",
    r"\bmember\s+(?:of\s+)?technical\s+staff\b",
    r"\bmts\s*[-_]?\s*1\b",
    r"\bmts\s*[-_]?\s*i\b",
    r"\bamts\b",
    r"\bassociate\s+technical\s+staff\b",
    r"\b0\s*[-_to]+\s*[12]\s*years?\b",
    r"\b1\s*[-_to]+\s*2\s*years?\b",
    r"\b202[5-7]\b",
]

STRONG_JUNIOR_TITLE_PATTERNS = [
    r"\bintern\b",
    r"\binternship\b",
    r"\bfresher\b",
    r"\btrainee\b",
    r"\bjunior\b",
    r"\bjr\b",
    r"\bgraduate\b",
    r"\bentry\s*level\b",
    r"\bsde\s*[-_]?\s*1\b",
    r"\bmts\s*[-_]?\s*1\b",
    r"\bamts\b",
]


def is_fresh_posting(date_str: str, max_hours: int = HOURS_OLD) -> bool:
    """
    Validates that a job posting date falls within the max_hours freshness threshold.
    Rejects stale postings (e.g. 1 month old). If date_str is omitted, returns True.
    """
    if not date_str:
        return True
    try:
        clean = str(date_str).strip().replace("Z", "+00:00")
        if "T" in clean:
            parts = clean.split("T")
            date_part = parts[0]
            time_part = parts[1].split("+")[0].split("-")[0]
            if "." in time_part:
                main_time, micro = time_part.split(".", 1)
                micro = (micro + "000000")[:6]
                clean_iso = f"{date_part}T{main_time}.{micro}+00:00"
            else:
                clean_iso = f"{date_part}T{time_part}+00:00"
            posted_dt = datetime.fromisoformat(clean_iso)
        else:
            posted_dt = datetime.strptime(clean[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        age_seconds = (now - posted_dt).total_seconds()
        if age_seconds > (max_hours + 12) * 3600:
            return False
        return True
    except Exception:
        return True


def is_suitable_for_graduate(job: dict[str, Any]) -> bool:
    """
    Evaluates whether a job posting matches a 2027 graduate with 0-2 years experience.
    Allows Member of Technical Staff (MTS-1) while rejecting Staff Software Engineer.
    Requires at least 60 characters of descriptive text to enable meaningful AI evaluation.

    Evaluation precedence:
    1. Reject stale listings older than HOURS_OLD (3-4 days).
    2. Hard reject irrelevant stacks (PHP/Laravel, .NET/C#, Android/iOS/Flutter, Salesforce/SAP).
    3. Hard reject explicit senior titles.
    4. Reject explicit senior experience (3+ to 12+ years) unless title is strongly junior.
    5. Accept on positive junior / fresher / intern indicators.
    6. Accept unleveled technical titles by default.
    """
    title = str(job.get("title", "")).lower()
    description = str(job.get("description", "")).lower()
    date_posted = str(job.get("date_posted") or "")

    if len(description.strip()) < 60:
        return False

    if not is_fresh_posting(date_posted):
        return False

    for pattern in IRRELEVANT_ROLE_PATTERNS:
        if re.search(pattern, title):
            return False

    for pattern in SENIOR_TITLE_PATTERNS:
        if re.search(pattern, title):
            return False

    has_senior_exp = any(re.search(pat, description) for pat in SENIOR_EXP_PATTERNS)
    if has_senior_exp:
        return any(re.search(pat, title) for pat in STRONG_JUNIOR_TITLE_PATTERNS)

    has_junior_indicator = any(
        re.search(pat, title) or re.search(pat, description)
        for pat in JUNIOR_POSITIVE_PATTERNS
    )
    if has_junior_indicator:
        return True

    return True


def filter_suitable_jobs(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Filters an iterable of jobs, removing senior, excessive-experience, and stub postings.
    Maintains ordering while discarding unsuitable positions.
    """
    return [job for job in jobs if is_suitable_for_graduate(job)]
