"""
SQLite persistence layer.

Tables:
  jobs        – one row per active job (upserted each run)
  runs        – audit log of each scrape run
  snapshots   – per-run aggregate counts for trend tracking
"""

import json
import sqlite3
import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path

from config import DB_PATH

logger = logging.getLogger(__name__)


def _connect() -> sqlite3.Connection:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS jobs (
                job_id          TEXT NOT NULL,
                company         TEXT NOT NULL,
                title           TEXT NOT NULL,
                department      TEXT,
                location        TEXT,
                url             TEXT,
                content_hash    TEXT,
                content         TEXT,
                job_category    TEXT,
                vertical_domains TEXT,   -- JSON array
                first_seen      TEXT NOT NULL,
                last_seen       TEXT NOT NULL,
                is_active       INTEGER NOT NULL DEFAULT 1,
                ai_summary      TEXT,
                PRIMARY KEY (job_id, company)
            );

            CREATE TABLE IF NOT EXISTS runs (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                run_at          TEXT NOT NULL,
                run_type        TEXT NOT NULL,   -- 'initial' | 'weekly'
                jobs_total      INTEGER,
                jobs_added      INTEGER,
                jobs_removed    INTEGER,
                report_path     TEXT
            );

            CREATE TABLE IF NOT EXISTS snapshots (
                id                    INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_at           TEXT NOT NULL,
                company               TEXT NOT NULL,
                total_active          INTEGER NOT NULL,
                categories_json       TEXT NOT NULL,       -- {category_key: count}
                vertical_domains_json TEXT NOT NULL        -- {domain_key: count}
            );
        """)
    logger.info("Database initialised at %s", DB_PATH)
    _migrate_db()


def _hash(content: str) -> str:
    return hashlib.md5(content.encode("utf-8", errors="replace")).hexdigest()


def get_active_job_ids() -> set[tuple[str, str]]:
    """Return set of (job_id, company) currently marked active."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT job_id, company FROM jobs WHERE is_active = 1"
        ).fetchall()
    return {(r["job_id"], r["company"]) for r in rows}


def upsert_jobs(jobs: list[dict]) -> dict:
    """
    Insert new jobs; update last_seen for existing ones.
    Returns {"added": [...], "updated": [...]} with full job dicts.
    """
    now = datetime.now(timezone.utc).isoformat()
    added, updated = [], []

    with _connect() as conn:
        for job in jobs:
            key = (job["job_id"], job["company"])
            existing = conn.execute(
                "SELECT content_hash, is_active FROM jobs WHERE job_id=? AND company=?",
                key,
            ).fetchone()

            h = _hash(job.get("content", ""))
            vd = json.dumps(job.get("vertical_domains", []))

            if existing is None:
                conn.execute(
                    """INSERT INTO jobs
                       (job_id, company, title, department, location, url,
                        content_hash, content, job_category, vertical_domains,
                        first_seen, last_seen, is_active)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,1)""",
                    (
                        job["job_id"], job["company"], job["title"],
                        job.get("department", ""), job.get("location", ""),
                        job.get("url", ""), h, job.get("content", ""),
                        job.get("job_category", "other"), vd, now, now,
                    ),
                )
                added.append(job)
            else:
                conn.execute(
                    """UPDATE jobs SET last_seen=?, content_hash=?, content=?,
                       job_category=?, vertical_domains=?, is_active=1,
                       title=?, department=?, location=?, url=?
                       WHERE job_id=? AND company=?""",
                    (
                        now, h, job.get("content", ""),
                        job.get("job_category", "other"), vd,
                        job["title"], job.get("department", ""),
                        job.get("location", ""), job.get("url", ""),
                        job["job_id"], job["company"],
                    ),
                )
                if not existing["is_active"]:
                    updated.append(job)  # reappeared

    return {"added": added, "updated": updated}


def mark_removed(current_ids: set[tuple[str, str]]) -> tuple[int, list[dict]]:
    """
    Mark jobs no longer in the API response as inactive.
    Returns (removed_count, list_of_removed_job_dicts).
    """
    now = datetime.now(timezone.utc).isoformat()
    removed_jobs = []
    with _connect() as conn:
        active = conn.execute(
            "SELECT * FROM jobs WHERE is_active = 1"
        ).fetchall()
        for row in active:
            key = (row["job_id"], row["company"])
            if key not in current_ids:
                conn.execute(
                    "UPDATE jobs SET is_active=0, last_seen=? WHERE job_id=? AND company=?",
                    (now, row["job_id"], row["company"]),
                )
                removed_jobs.append(dict(row))
    return len(removed_jobs), removed_jobs


def _migrate_db():
    """Add columns introduced after the initial schema creation."""
    with _connect() as conn:
        try:
            conn.execute("ALTER TABLE jobs ADD COLUMN ai_summary TEXT")
            logger.info("Migrated: added ai_summary column")
        except Exception:
            pass  # column already exists


def get_jobs_needing_summary() -> list[dict]:
    """Return active vertical-domain jobs that don't yet have an AI summary."""
    with _connect() as conn:
        rows = conn.execute(
            """SELECT * FROM jobs
               WHERE is_active = 1
                 AND (ai_summary IS NULL OR ai_summary = '')
                 AND vertical_domains != '[]'
                 AND vertical_domains IS NOT NULL"""
        ).fetchall()
    return [dict(r) for r in rows]


def save_summaries(summaries: dict):
    """Persist {(job_id, company): summary_text} to the database."""
    with _connect() as conn:
        for (job_id, company), summary in summaries.items():
            if summary:
                conn.execute(
                    "UPDATE jobs SET ai_summary=? WHERE job_id=? AND company=?",
                    (summary, job_id, company),
                )


def get_all_active_jobs() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM jobs WHERE is_active = 1 ORDER BY company, title"
        ).fetchall()
    return [dict(r) for r in rows]


def log_run(run_type: str, jobs_total: int, jobs_added: int,
            jobs_removed: int, report_path: str):
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute(
            """INSERT INTO runs (run_at, run_type, jobs_total, jobs_added,
               jobs_removed, report_path) VALUES (?,?,?,?,?,?)""",
            (now, run_type, jobs_total, jobs_added, jobs_removed, report_path),
        )


def save_snapshot(all_active_jobs: list[dict]):
    """Save per-company aggregate counts for trend tracking."""
    from collections import Counter
    from config import COMPANIES

    now = datetime.now(timezone.utc).isoformat()

    with _connect() as conn:
        for company in COMPANIES:
            jobs = [j for j in all_active_jobs if j["company"] == company]

            cat_counts: Counter = Counter(j.get("job_category", "other") for j in jobs)

            dom_counts: Counter = Counter()
            for j in jobs:
                raw = j.get("vertical_domains", "[]")
                domains = json.loads(raw) if isinstance(raw, str) else (raw or [])
                for d in domains:
                    dom_counts[d] += 1

            conn.execute(
                """INSERT INTO snapshots
                   (snapshot_at, company, total_active, categories_json, vertical_domains_json)
                   VALUES (?, ?, ?, ?, ?)""",
                (now, company, len(jobs),
                 json.dumps(dict(cat_counts)),
                 json.dumps(dict(dom_counts))),
            )
    logger.info("Snapshot saved (%d active jobs total)", len(all_active_jobs))


def get_snapshots() -> list[dict]:
    """Return all snapshots ordered by time, with parsed JSON fields."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM snapshots ORDER BY snapshot_at"
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["categories"] = json.loads(d.pop("categories_json"))
        d["vertical_domains"] = json.loads(d.pop("vertical_domains_json"))
        result.append(d)
    return result


def get_last_run() -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM runs ORDER BY id DESC LIMIT 1"
        ).fetchone()
    return dict(row) if row else None
