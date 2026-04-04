"""
Fetch jobs from two ATS providers:
  - Ashby HQ  (OpenAI)    : https://api.ashbyhq.com/posting-api/job-board/{board}
  - Greenhouse (Anthropic) : https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true

Both return a normalised dict with keys:
  job_id, company, title, department, location, url, content, updated_at, fetched_at
"""

import time
import logging
from datetime import datetime, timezone

import requests

from config import COMPANIES

logger = logging.getLogger(__name__)

GREENHOUSE_API = "https://boards-api.greenhouse.io/v1/boards/{board}/jobs"
ASHBY_API      = "https://api.ashbyhq.com/posting-api/job-board/{board}"
REQUEST_TIMEOUT = 30
RETRY_ATTEMPTS  = 3
RETRY_DELAY     = 5


# ── low-level HTTP ────────────────────────────────────────────────────────────

def _get(url: str, params: dict | None = None) -> dict:
    headers = {"User-Agent": "job-tracker/1.0 (private research tool)"}
    for attempt in range(RETRY_ATTEMPTS):
        try:
            r = requests.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            if attempt < RETRY_ATTEMPTS - 1:
                logger.warning("Request failed (%s), retrying in %ds…", e, RETRY_DELAY)
                time.sleep(RETRY_DELAY)
            else:
                raise


# ── Greenhouse normaliser ─────────────────────────────────────────────────────

def _norm_greenhouse(raw: dict, company_key: str) -> dict:
    dept_names = [d["name"] for d in raw.get("departments", []) if d.get("name")]
    return {
        "job_id":     str(raw["id"]),
        "company":    company_key,
        "title":      raw.get("title", "").strip(),
        "department": dept_names[0] if dept_names else "",
        "location":   raw.get("location", {}).get("name", ""),
        "url":        raw.get("absolute_url", ""),
        "content":    raw.get("content", ""),
        "updated_at": raw.get("updated_at", ""),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def _fetch_greenhouse(company_key: str, board: str) -> list[dict]:
    url  = GREENHOUSE_API.format(board=board)
    data = _get(url, params={"content": "true"})
    raw_jobs = data.get("jobs", [])
    logger.info("  → %d jobs found (Greenhouse)", len(raw_jobs))
    return [_norm_greenhouse(j, company_key) for j in raw_jobs]


# ── Ashby normaliser ──────────────────────────────────────────────────────────

def _norm_ashby(raw: dict, company_key: str) -> dict:
    # Location: prefer address city/state, fall back to location name
    addr = raw.get("address") or {}
    city  = addr.get("city", "")
    state = addr.get("state", "")
    if city and state:
        loc = f"{city}, {state}"
    elif city:
        loc = city
    else:
        loc = raw.get("location", "") or ""
    if raw.get("isRemote"):
        loc = loc + " (Remote)" if loc else "Remote"

    return {
        "job_id":     str(raw["id"]),
        "company":    company_key,
        "title":      raw.get("title", "").strip(),
        "department": raw.get("team", raw.get("department", "")),
        "location":   loc,
        "url":        raw.get("jobUrl", ""),
        "content":    raw.get("descriptionHtml", "") or raw.get("descriptionPlain", ""),
        "updated_at": raw.get("publishedAt", ""),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def _fetch_ashby(company_key: str, board: str) -> list[dict]:
    url  = ASHBY_API.format(board=board)
    data = _get(url)
    raw_jobs = data.get("jobs", [])
    logger.info("  → %d jobs found (Ashby)", len(raw_jobs))
    return [_norm_ashby(j, company_key) for j in raw_jobs]


# ── public API ────────────────────────────────────────────────────────────────

def fetch_company_jobs(company_key: str) -> list[dict]:
    cfg = COMPANIES[company_key]
    logger.info("Fetching %s jobs…", cfg["label"])
    api_type = cfg.get("api_type", "greenhouse")

    if api_type == "ashby":
        return _fetch_ashby(company_key, cfg["ashby_board"])
    else:
        return _fetch_greenhouse(company_key, cfg["greenhouse_board"])


def fetch_all_jobs() -> list[dict]:
    all_jobs = []
    for company_key in COMPANIES:
        jobs = fetch_company_jobs(company_key)
        all_jobs.extend(jobs)
        time.sleep(1)
    return all_jobs
