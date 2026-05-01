import os
import sys
from celery import Celery
from config import EnvConfig

# Add project root to sys.path for task imports
sys.path.insert(0, str(EnvConfig.PROJECT_ROOT()))

# Initialize Celery
app = Celery(
    "edupredict_worker",
    broker=EnvConfig.CELERY_BROKER_URL(),
    backend=EnvConfig.CELERY_RESULT_BACKEND(),
    include=["app.api.tasks"]
)

# Optional configuration
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600, # 1 hour max
)

if __name__ == "__main__":
    app.start()
