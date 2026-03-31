import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.api import events, map
from app.tasks.ingest import start_scheduler, stop_scheduler, run_full_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="FixMyCity API",
    description="Urban hazard detection and reporting platform.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(events.router)
app.include_router(map.router)


@app.on_event("startup")
def on_startup():
    logger.info("Initialising database...")
    init_db()
    logger.info("Starting background scheduler...")
    start_scheduler()
    logger.info("Running initial pipeline pass...")
    run_full_pipeline()


@app.on_event("shutdown")
def on_shutdown():
    stop_scheduler()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/admin/trigger-pipeline", tags=["admin"])
def trigger_pipeline():
    """Manually trigger ingestion + processing."""
    run_full_pipeline()
    return {"status": "triggered"}
