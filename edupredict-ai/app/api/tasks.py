import logging
from app.api.worker import app as celery_app
from model.retrain_with_temporal import retrain
from data.pipeline.dag import run_dag
from data.pipeline.save_snapshot import save_snapshot
import asyncio
import os

logger = logging.getLogger(__name__)

RETRAIN_LOCK_KEY = "edupredict:retrain_lock"
RETRAIN_LOCK_TTL = 3600  # 1 hour hard cap

@celery_app.task(name="tasks.run_acquisition_pipeline")
def run_acquisition_pipeline():
    """
    Celery task to run the data acquisition DAG and save a snapshot.
    """
    try:
        logger.info("Celery: Starting data acquisition pipeline")
        asyncio.run(run_dag())
        save_snapshot()
        logger.info("Celery: Data acquisition pipeline complete")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Celery: Data acquisition failed: {e}")
        raise e

@celery_app.task(bind=True, name="tasks.retrain_model", max_retries=0)
def retrain_model(self) -> dict:
    import redis as sync_redis
    from datetime import datetime, timezone
    from config import EnvConfig, ROOT_DIR

    run_id   = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    log_dir  = ROOT_DIR / "logs"
    log_dir.mkdir(exist_ok=True)
    log_path = log_dir / f"retrain_{run_id}.log"

    r = sync_redis.from_url(EnvConfig.REDIS_URL())

    # Acquire lock — NX means only set if key does not exist
    acquired = r.set(RETRAIN_LOCK_KEY, run_id, nx=True, ex=RETRAIN_LOCK_TTL)
    if not acquired:
        existing = r.get(RETRAIN_LOCK_KEY)
        return {"status": "aborted", "reason": f"Already running: {existing.decode() if existing else 'unknown'}"}

    import time, subprocess
    start = time.time()
    try:
        with open(log_path, "w") as lf:
            lf.write(f"=== EduPredict AI Retrain {run_id} ===\n\n")
            lf.flush()
            proc = subprocess.run(
                ["python3", str(ROOT_DIR / "run_pipeline.py"), "--retrain"],
                stdout=lf,
                stderr=lf,
                cwd=str(ROOT_DIR),
                timeout=3000,
            )
        duration = round(time.time() - start, 1)
        if proc.returncode == 0:
            return {"status": "success", "run_id": run_id,
                    "log_path": str(log_path), "duration_seconds": duration}
        return {"status": "failed", "run_id": run_id, "exit_code": proc.returncode,
                "log_path": str(log_path), "duration_seconds": duration}
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "run_id": run_id, "log_path": str(log_path)}
    except Exception as e:
        logger.exception(f"Retrain {run_id} error")
        return {"status": "error", "run_id": run_id, "error": str(e)}
    finally:
        # Only release if this run still holds the lock
        current = r.get(RETRAIN_LOCK_KEY)
        if current and current.decode() == run_id:
            r.delete(RETRAIN_LOCK_KEY)
