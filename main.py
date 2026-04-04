"""
Job Tracker CLI

Usage:
  python main.py initial   -- first run: fetch all, generate full report
  python main.py weekly    -- subsequent runs: find new jobs, generate update

The script auto-detects whether a DB exists and defaults to the right mode.
"""

import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import click

import database
import scraper
import summarizer
import analyzer
import reporter
from config import COMPANIES

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def _open_report(path: str):
    """Open HTML report in the default browser."""
    try:
        os.startfile(path)  # Windows
    except AttributeError:
        subprocess.Popen(["xdg-open", path])


def _run_initial():
    logger.info("=== INITIAL RUN ===")
    database.init_db()

    logger.info("Fetching jobs from Greenhouse API…")
    raw_jobs = scraper.fetch_all_jobs()
    logger.info("Total fetched: %d", len(raw_jobs))

    logger.info("Classifying jobs…")
    jobs = [analyzer.enrich_job(j) for j in raw_jobs]

    logger.info("Saving to database…")
    result = database.upsert_jobs(jobs)
    current_ids = {(j["job_id"], j["company"]) for j in jobs}
    database.mark_removed(current_ids)  # nothing to remove on first run

    logger.info("Generating AI summaries for vertical-domain jobs…")
    jobs_needing = database.get_jobs_needing_summary()
    if jobs_needing:
        sums = summarizer.generate_summaries(jobs_needing)
        database.save_summaries(sums)

    logger.info("Saving snapshot for trend tracking…")
    all_jobs = database.get_all_active_jobs()
    database.save_snapshot(all_jobs)

    logger.info("Generating initial report…")
    report_path = reporter.generate_initial_report(all_jobs)

    database.log_run(
        run_type="initial",
        jobs_total=len(all_jobs),
        jobs_added=len(result["added"]),
        jobs_removed=0,
        report_path=report_path,
    )

    domains = sum(
        1 for j in all_jobs
        if j.get("vertical_domains") and j["vertical_domains"] != "[]"
    )
    click.echo(f"\n[OK] Initial report: {report_path}")
    click.echo(f"  OpenAI jobs         : {sum(1 for j in all_jobs if j['company']=='openai')}")
    click.echo(f"  Anthropic jobs      : {sum(1 for j in all_jobs if j['company']=='anthropic')}")
    click.echo(f"  Total               : {len(all_jobs)}")
    click.echo(f"  Vertical-domain jobs: {domains}")
    return report_path


def _run_weekly():
    logger.info("=== WEEKLY UPDATE ===")
    database.init_db()

    last_run = database.get_last_run()
    if not last_run:
        click.echo(
            "No previous run found. Running initial mode instead.", err=True
        )
        return _run_initial()

    since = last_run["run_at"]
    since_dt = datetime.fromisoformat(since).strftime("%Y-%m-%d %H:%M UTC")

    logger.info("Last run: %s  — looking for new jobs since then", since_dt)

    raw_jobs = scraper.fetch_all_jobs()
    jobs = [analyzer.enrich_job(j) for j in raw_jobs]

    result = database.upsert_jobs(jobs)
    current_ids = {(j["job_id"], j["company"]) for j in jobs}
    removed_count, removed_jobs = database.mark_removed(current_ids)

    new_jobs = result["added"]
    logger.info("New jobs: %d  |  Removed/closed: %d", len(new_jobs), removed_count)

    logger.info("Generating AI summaries for vertical-domain jobs...")
    jobs_needing = database.get_jobs_needing_summary()
    if jobs_needing:
        sums = summarizer.generate_summaries(jobs_needing)
        database.save_summaries(sums)

    all_jobs = database.get_all_active_jobs()
    database.save_snapshot(all_jobs)

    snapshots = database.get_snapshots()
    report_path = reporter.generate_weekly_report(new_jobs, since_dt,
                      snapshots=snapshots, all_jobs=all_jobs, removed_jobs=removed_jobs)

    database.log_run(
        run_type="weekly",
        jobs_total=len(all_jobs),
        jobs_added=len(new_jobs),
        jobs_removed=removed_count,
        report_path=report_path,
    )

    new_vertical = sum(
        1 for j in new_jobs
        if j.get("vertical_domains") and j["vertical_domains"] != "[]"
    )
    removed_vertical = sum(
        1 for j in removed_jobs
        if j.get("vertical_domains") and j["vertical_domains"] != "[]"
    )
    click.echo(f"\n[OK] Weekly update report: {report_path}")
    click.echo(f"  New jobs total       : {len(new_jobs)}")
    click.echo(f"  New vertical-domain  : {new_vertical}")
    click.echo(f"  Closed/removed       : {removed_count} (vertical: {removed_vertical})")
    return report_path


@click.command()
@click.argument("mode", default="auto",
                type=click.Choice(["initial", "weekly", "auto"], case_sensitive=False))
@click.option("--open/--no-open", "open_report", default=True,
              help="Open report in browser after generation (default: yes)")
def main(mode: str, open_report: bool):
    """
    Fetch AI company job listings and generate HTML reports.

    \b
    MODE:
      initial  First run — full snapshot + stats
      weekly   Incremental update since last run
      auto     Detect automatically (default)
    """
    # Auto-detect
    if mode == "auto":
        last = database.get_last_run() if Path("data/jobs.db").exists() else None
        mode = "weekly" if last else "initial"
        logger.info("Auto-detected mode: %s", mode)

    if mode == "initial":
        path = _run_initial()
    else:
        path = _run_weekly()

    if open_report and path:
        _open_report(path)


if __name__ == "__main__":
    main()
