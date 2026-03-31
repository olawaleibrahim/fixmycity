"""
Scheduled ingestion + processing pipeline.
Uses APScheduler (no Redis needed for MVP).
Runs once on startup, then every hour.
"""

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.database import SessionLocal
from app.ingestion import ingest_all
from app.processing.nlp.pipeline import run_pipeline

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def run_full_pipeline():
    """Ingest all sources then process unprocessed posts."""
    db = SessionLocal()
    try:
        counts = ingest_all(db)
        new_events = run_pipeline(db)
        logger.info(
            "Pipeline complete | ingested=%s | events_created=%d",
            counts,
            new_events,
        )
    except Exception as exc:
        logger.error("Pipeline error: %s", exc, exc_info=True)
    finally:
        db.close()


def start_scheduler():
    global _scheduler
    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        run_full_pipeline,
        trigger="interval",
        hours=1,
        id="ingest_pipeline",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("Scheduler started — pipeline runs every hour.")


def stop_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
