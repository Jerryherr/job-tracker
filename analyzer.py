"""
Classify jobs into categories and detect vertical industry domains.
Matching against title (high weight) + stripped HTML content.
"""

import re
from bs4 import BeautifulSoup
from config import JOB_CATEGORIES, VERTICAL_DOMAINS


def _strip_html(html: str) -> str:
    if not html:
        return ""
    return BeautifulSoup(html, "html.parser").get_text(" ", strip=True)


def _text_for_matching(title: str, content_html: str) -> tuple[str, str]:
    """Return (title_lower, content_lower) ready for keyword search."""
    title_lower = title.lower()
    content_lower = _strip_html(content_html).lower()
    return title_lower, content_lower


def _keyword_hit(keyword: str, title: str, content: str) -> bool:
    """True if keyword appears as a whole word/phrase in title or content."""
    pattern = r"\b" + re.escape(keyword) + r"\b"
    return bool(re.search(pattern, title)) or bool(re.search(pattern, content))


def classify_job_category(title: str, content_html: str) -> str:
    """Return the first matching category key, or 'other'."""
    t, c = _text_for_matching(title, content_html)
    for cat in JOB_CATEGORIES:
        for kw in cat["keywords"]:
            if _keyword_hit(kw, t, c):
                return cat["key"]
    return "other"


def detect_vertical_domains(title: str, content_html: str) -> list[str]:
    """
    Return list of vertical domain keys found in title/content.
    Title match counts more — a title hit alone is sufficient.
    Content match requires a stricter threshold (keyword must appear 2+
    times to reduce false positives from boilerplate).
    """
    t, c = _text_for_matching(title, content_html)
    found = []
    for domain_key, domain in VERTICAL_DOMAINS.items():
        matched_in_title = any(_keyword_hit(kw, t, "") for kw in domain["keywords"])
        if matched_in_title:
            found.append(domain_key)
            continue
        # Content: count distinct keyword hits
        content_hits = sum(
            1 for kw in domain["keywords"] if _keyword_hit(kw, "", c)
        )
        if content_hits >= 2:
            found.append(domain_key)
    return found


def enrich_job(job: dict) -> dict:
    """Add category and vertical_domains to a job dict (in-place + return)."""
    title = job.get("title", "")
    content = job.get("content", "")
    job["job_category"] = classify_job_category(title, content)
    job["vertical_domains"] = detect_vertical_domains(title, content)
    return job
