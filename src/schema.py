"""
Shared job schema and text sanitization for the Job Scraper MCP server.

Produces detailed, normalized dictionary representations of job postings.
Generates cryptographically signed HMAC-SHA256 unique identifiers using HMAC_SECRET_KEY
across normalized title and company for deterministic cross-board deduplication
(the same job on LinkedIn, Indeed, and Adzuna collapses to one record).
Enriches descriptions with structured headers (Role, Company, Location, Type, Salary)
to provide maximum evaluative context for Gemini Spark.
"""
from __future__ import annotations

import hashlib
import hmac
import html
import re
from typing import Any

from src.config import DESC_LIMIT, HMAC_SECRET_KEY


def clean_text(raw_text: str, max_chars: int = DESC_LIMIT) -> str:
    """
    Strips HTML markup, decodes entity symbols, and collapses repeated whitespace.
    Trims the output string to the configured maximum character cutoff.
    """
    if not raw_text:
        return ""
    text = html.unescape(raw_text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]


def job_id(title: str, company: str, location: str = "", date_posted: str = "", link: str = "") -> str:
    """
    Generates a deterministic 16-character HMAC-SHA256 signature using HMAC_SECRET_KEY.
    Hashes only normalized alphanumeric title and company so the same job cross-listed
    on LinkedIn, Indeed, Adzuna, and Jooble resolves to one identical ID for
    cross-board deduplication. Link and date_posted are aggregator-specific and
    intentionally excluded. Remaining parameters are accepted for backward
    compatibility with existing call sites.
    """
    clean_title = re.sub(r"[^a-z0-9]", "", (title or "").lower())
    clean_company = re.sub(r"[^a-z0-9]", "", (company or "").lower())
    raw = f"{clean_title}|{clean_company}"
    return hmac.new(
        HMAC_SECRET_KEY.encode("utf-8"),
        raw.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()[:16]


def norm(
    source: str,
    title: Any,
    company: Any,
    job_link: Any,
    company_link: Any,
    description: Any,
    location: Any,
    date_posted: Any,
    apply_link: Any = None,
    job_type: Any = None,
    is_remote: Any = None,
    salary: Any = None,
) -> dict[str, Any]:
    """
    Normalizes arbitrary scraper inputs into the canonical job record shape.
    Computes an HMAC job identifier, strips HTML, and structures description context.
    """
    cleaned_title = clean_text(str(title or ""), max_chars=150)
    cleaned_company = clean_text(str(company or ""), max_chars=100)
    cleaned_location = clean_text(str(location or ""), max_chars=100)
    cleaned_date = str(date_posted or "").strip()
    cleaned_job_link = str(job_link or "").strip()
    cleaned_apply_link = str(apply_link or cleaned_job_link).strip()
    cleaned_type = clean_text(str(job_type or ""), max_chars=50)
    cleaned_salary = clean_text(str(salary or ""), max_chars=80)
    raw_desc = clean_text(str(description or ""))

    header_parts = []
    if cleaned_title:
        header_parts.append(f"Position: {cleaned_title}")
    if cleaned_company:
        header_parts.append(f"Company: {cleaned_company}")
    if cleaned_location:
        header_parts.append(f"Location: {cleaned_location}")
    if cleaned_type:
        header_parts.append(f"Job Type: {cleaned_type}")
    if cleaned_salary:
        header_parts.append(f"Salary: {cleaned_salary}")

    header_str = " | ".join(header_parts)
    if header_str and raw_desc:
        enriched_desc = f"{header_str}\n\nRequirements & Overview:\n{raw_desc}"
    else:
        enriched_desc = raw_desc or header_str

    final_desc = enriched_desc[:DESC_LIMIT]

    generated_id = job_id(cleaned_title, cleaned_company)

    return {
        "id": generated_id,
        "source": source,
        "title": cleaned_title,
        "company": cleaned_company,
        "location": cleaned_location,
        "job_link": cleaned_job_link,
        "apply_link": cleaned_apply_link,
        "company_link": str(company_link or "").strip(),
        "description": final_desc,
        "date_posted": cleaned_date,
        "job_type": cleaned_type,
        "is_remote": bool(is_remote) if is_remote is not None else None,
        "salary": cleaned_salary,
    }
