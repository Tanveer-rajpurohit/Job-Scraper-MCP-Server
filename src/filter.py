"""
Candidate suitability filter for 2027 graduate profile (0-2 years experience).

Evaluates scraped job postings against experience and seniority criteria:
- Targeted: Internships, PPO opportunities, Fresher / Entry-Level (0-1 year),
  Junior, Associate, SDE-1, and Member of Technical Staff (MTS-1/AMTS) roles.
- Excluded: Staff Software Engineer, Senior, Sr., Lead, Principal, Architect,
  Director, Manager, and postings explicitly demanding 3+ to 12+ years of experience.
- Excluded: Broken postings with trivial/empty descriptions (< 60 chars) lacking evaluative substance.
"""
from __future__ import annotations

import re
from typing import Any

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
    r"\bassociate\b",
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


def is_suitable_for_graduate(job: dict[str, Any]) -> bool:
    """
    Evaluates whether a job posting matches a 2027 graduate with 0-2 years experience.
    Allows Member of Technical Staff (MTS-1) while rejecting Staff Software Engineer.
    Requires at least 60 characters of descriptive text to enable meaningful AI evaluation.
    """
    title = str(job.get("title", "")).lower()
    description = str(job.get("description", "")).lower()

    if len(description.strip()) < 60:
        return False

    for pattern in SENIOR_TITLE_PATTERNS:
        if re.search(pattern, title):
            return False

    has_junior_indicator = any(
        re.search(pat, title) or re.search(pat, description)
        for pat in JUNIOR_POSITIVE_PATTERNS
    )

    if has_junior_indicator:
        return True

    for pattern in SENIOR_EXP_PATTERNS:
        if re.search(pattern, description):
            return False

    return True


def filter_suitable_jobs(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Filters an iterable of jobs, removing senior, excessive-experience, and stub postings.
    Maintains ordering while discarding unsuitable positions.
    """
    return [job for job in jobs if is_suitable_for_graduate(job)]
