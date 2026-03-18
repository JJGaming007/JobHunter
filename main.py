"""
Games QA Job Hunter — Main Orchestrator
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Runs on a schedule, scrapes all platforms, scores jobs,
sends email alerts, opens top matches in browser, and optionally
auto-applies via LinkedIn Easy Apply.

Usage:
    python main.py             ← runs forever (checks every N minutes)
    python main.py --once      ← single run then exit (good for testing)
"""

import sys
import logging
import webbrowser
import time
import schedule
from datetime import datetime

import config
from database import JobDatabase

# Silence noisy third-party loggers
logging.getLogger("JobSpy").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("selenium").setLevel(logging.WARNING)
from scrapers import scrape_all_platforms
from scorer import score_jobs
from notifier import send_job_notification
from auto_apply import run_auto_apply

# ── Logging setup ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler("job_hunter.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


# ── Core cycle ─────────────────────────────────────────────────────────────────

def run_job_hunt():
    start = datetime.now()
    logger.info("=" * 60)
    logger.info("🎮  Job hunt cycle started")
    logger.info("=" * 60)

    db = JobDatabase()

    # 1. Scrape all platforms
    all_jobs = scrape_all_platforms()
    if not all_jobs:
        logger.info("No jobs scraped this cycle.")
        return

    # 2. Score every job
    scored = score_jobs(all_jobs)

    # 3. Keep only new (not-yet-seen) jobs
    new_jobs = [j for j in scored if not db.is_seen(j.get("url", ""))]
    logger.info(f"New jobs (not seen before): {len(new_jobs)}")

    if not new_jobs:
        logger.info("Nothing new. See you next cycle.")
        return

    # 4. Persist all new jobs to DB
    for job in new_jobs:
        db.add_job(job)

    # 5. Filter by minimum relevance score
    qualified = [j for j in new_jobs if j.get("score", 0) >= config.MIN_RELEVANCE_SCORE]
    logger.info(f"Qualified jobs (score ≥ {config.MIN_RELEVANCE_SCORE}): {len(qualified)}")

    if not qualified:
        logger.info("No jobs met the minimum relevance threshold.")
        return

    # 6. Print summary to console
    _print_table(qualified)

    # 7. Send email digest
    send_job_notification(qualified, db=db)

    # 8. Auto-open top N in the default browser
    top_jobs = qualified[: config.BROWSER_OPEN_TOP_N]
    if top_jobs:
        logger.info(f"Opening top {len(top_jobs)} job(s) in browser...")
        for job in top_jobs:
            webbrowser.open(job["url"])
            db.mark_opened(job["url"])
            time.sleep(0.5)

    # 9. LinkedIn Easy Apply (only if enabled in config)
    if config.ENABLE_AUTO_APPLY:
        run_auto_apply(qualified, db=db)

    elapsed = (datetime.now() - start).total_seconds()
    logger.info(f"Cycle complete in {elapsed:.1f}s — {len(qualified)} qualified jobs processed.")


def _print_table(jobs: list):
    """Quick console table using plain text (no extra deps)."""
    print("\n" + "─" * 100)
    print(f"  {'#':<3}  {'Score':<6}  {'Title':<38}  {'Company':<22}  {'Platform':<14}  {'Easy Apply'}")
    print("─" * 100)
    for i, j in enumerate(jobs, 1):
        ea = "✓" if j.get("easy_apply") else ""
        print(
            f"  {i:<3}  {j.get('score', 0):<6}  "
            f"{(j.get('title') or '')[:37]:<38}  "
            f"{(j.get('company') or '')[:21]:<22}  "
            f"{(j.get('platform') or '')[:13]:<14}  {ea}"
        )
    print("─" * 100 + "\n")


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    once_mode = "--once" in sys.argv

    logger.info("🎮  Games QA Job Hunter starting up...")
    logger.info(f"   Platforms : {config.JOBSPY_PLATFORMS}")
    logger.info(f"   Naukri    : {config.ENABLE_NAUKRI}")
    logger.info(f"   Hitmarker : {config.ENABLE_HITMARKER}")
    logger.info(f"   AutoApply : {config.ENABLE_AUTO_APPLY}")
    logger.info(f"   Interval  : every {config.CHECK_INTERVAL_MINUTES} min")
    logger.info(f"   Min Score : {config.MIN_RELEVANCE_SCORE}/100")

    if once_mode:
        logger.info("Running in single-shot mode (--once).")
        run_job_hunt()
        sys.exit(0)

    # Run once immediately, then on schedule
    run_job_hunt()

    schedule.every(config.CHECK_INTERVAL_MINUTES).minutes.do(run_job_hunt)
    logger.info(f"Scheduler active. Next check in {config.CHECK_INTERVAL_MINUTES} minute(s). Press Ctrl+C to stop.")

    try:
        while True:
            schedule.run_pending()
            time.sleep(30)
    except KeyboardInterrupt:
        logger.info("Job Hunter stopped by user.")
