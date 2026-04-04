"""
Generate one-sentence AI summaries for vertical-domain jobs using Claude Haiku.
Results are cached in the database — each job is only summarized once.
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import anthropic
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def _strip_html(html: str) -> str:
    return BeautifulSoup(html or "", "html.parser").get_text(" ", strip=True)


def _summarize_one(job: dict) -> tuple[str, str, str]:
    """Return (job_id, company, summary). Retries once on rate-limit."""
    title = job.get("title", "")
    content = _strip_html(job.get("content", ""))[:900]
    nl = "\n"
    prompt = (
        "Job title: " + title + nl + nl
        + "Job description excerpt:" + nl + content + nl + nl
        + "Write ONE sentence (max 30 words) describing what this person does "
        + "day-to-day. Focus on the actual work, not company mission. "
        + "Start with a verb. No bullet points."
    )
    for attempt in range(2):
        try:
            msg = _get_client().messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=80,
                messages=[{"role": "user", "content": prompt}],
            )
            return job["job_id"], job["company"], msg.content[0].text.strip().rstrip(".")
        except anthropic.RateLimitError:
            if attempt == 0:
                time.sleep(5)
            else:
                return job["job_id"], job["company"], ""
        except Exception as e:
            logger.warning("Summary failed for %s: %s", title, e)
            return job["job_id"], job["company"], ""


def generate_summaries(jobs: list[dict], max_workers: int = 5) -> dict[tuple, str]:
    """
    Generate summaries for a list of jobs in parallel.
    Returns {(job_id, company): summary_text}.
    """
    if not jobs:
        return {}
    logger.info("Generating AI summaries for %d vertical-domain jobs...", len(jobs))
    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_summarize_one, j): j for j in jobs}
        done = 0
        for future in as_completed(futures):
            job_id, company, summary = future.result()
            results[(job_id, company)] = summary
            done += 1
            if done % 20 == 0 or done == len(jobs):
                logger.info("  Summarized %d / %d", done, len(jobs))
    return results
