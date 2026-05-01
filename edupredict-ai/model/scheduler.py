"""
Automated scheduler for EduPredict AI production operations.

Schedule:
  Every 6 hours:  Run data acquisition DAG → save snapshot
  Every 24 hours: Run drift check on last 200 API predictions
  On drift alert:  Trigger retraining pipeline
  
Uses APScheduler (no external orchestrator needed for this scale).
For production at scale: replace with Apache Airflow or Prefect.

Retraining is idempotent: if a run is already in progress,
the new trigger is dropped (not queued). This prevents runaway
parallel training jobs.
"""

import asyncio
import logging
import json
import os
import sys
import threading
import time
from pathlib import Path
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from config import EnvConfig

logger = logging.getLogger(__name__)

_retrain_lock = threading.Lock()
_retrain_in_progress = False


def run_dag_job():
    """Job: dispatch data acquisition DAG to Celery."""
    try:
        from app.api.tasks import run_acquisition_pipeline
        run_acquisition_pipeline.delay()
        logger.info("Scheduler: Dispatched DAG run to Celery")
    except Exception as e:
        logger.error(f"Scheduler: Failed to dispatch DAG run: {e}")


def run_drift_check_job():
    """Job: check feature drift and dispatch retraining if needed."""
    try:
        import sqlite3
        import numpy as np
        import pandas as pd
        from model.monitoring import check_drift

        monitoring_db = EnvConfig.DATA_DIR() / "monitoring.db"
        if not monitoring_db.exists():
            logger.info("No monitoring DB yet — skipping drift check")
            return

        conn = sqlite3.connect(monitoring_db)
        try:
            rows = conn.execute(
                "SELECT features_json, prediction FROM api_calls "
                "ORDER BY created_at DESC LIMIT 200"
            ).fetchall()
        except sqlite3.OperationalError:
            logger.info("api_calls table not yet populated — skipping")
            conn.close()
            return
        conn.close()

        if len(rows) < 50:
            logger.info(f"Only {len(rows)} API calls logged — need ≥50 for drift check")
            return

        feature_rows = [json.loads(r[0]) for r in rows]
        predictions = np.array([r[1] for r in rows])
        df = pd.DataFrame(feature_rows)

        metrics_path = EnvConfig.PROD_ARTIFACTS_DIR() / "metrics.json"
        if not metrics_path.exists():
            logger.warning("metrics.json not found — skipping drift check")
            return
            
        feature_names = json.loads(metrics_path.read_text()).get("feature_cols_v3", [])
        report = check_drift(df, predictions, feature_names)

        if report["retrain_recommended"]:
            logger.warning(f"Drift detected! Dispatching retraining task. Reasons: {report['retrain_reasons']}")
            from app.api.tasks import run_retraining_pipeline
            run_retraining_pipeline.delay()

    except Exception as e:
        logger.error(f"Drift check failed: {e}", exc_info=True)


def run_retraining_job():
    """Manual trigger for retraining via Celery."""
    from app.api.tasks import run_retraining_pipeline
    run_retraining_pipeline.delay()
    logger.info("Scheduler: Manually dispatched retraining task to Celery")


def create_scheduler() -> BackgroundScheduler:
    """Create and configure the production scheduler."""
    scheduler = BackgroundScheduler(
        job_defaults={"misfire_grace_time": 300, "coalesce": True}
    )

    dag_interval_hours = EnvConfig.DAG_INTERVAL_HOURS()
    scheduler.add_job(
        run_dag_job,
        trigger=IntervalTrigger(hours=dag_interval_hours),
        id="dag_refresh",
        name="Demand DAG refresh",
        replace_existing=True
    )

    scheduler.add_job(
        run_drift_check_job,
        trigger=CronTrigger(hour=2, minute=0),   # Daily at 2am
        id="drift_check",
        name="Feature drift monitoring",
        replace_existing=True
    )

    logger.info(
        f"Scheduler configured: DAG every {dag_interval_hours}h, "
        f"drift check daily at 02:00"
    )
    return scheduler
