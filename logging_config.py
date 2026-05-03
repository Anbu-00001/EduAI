"""
Centralised logging configuration for EduPredict AI.

Log levels:
  DEBUG   — detailed internal state (dev only)
  INFO    — normal operation events
  WARNING — degraded mode (fallback used, cache stale, etc.)
  ERROR   — operation failed but system continues
  CRITICAL — system cannot function, requires immediate attention

Log format includes:
  - ISO timestamp with timezone
  - Log level
  - Module name (not root logger)
  - Function name
  - Line number
  - Message

JSON logging available for production (parse by Prometheus/Grafana).
"""

import logging
import logging.config
import os
import json
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """Structured JSON log formatter for production monitoring."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)


def configure_logging(
    level: str = None,
    json_format: bool = None
) -> None:
    """
    Configure application-wide logging.
    Call once at application startup.
    
    level: DEBUG/INFO/WARNING/ERROR (defaults to INFO, or LOG_LEVEL env var)
    json_format: True for production JSON logs (defaults to LOG_FORMAT=json env var)
    """
    if level is None:
        level = os.environ.get("LOG_LEVEL", "INFO").upper()
    if json_format is None:
        json_format = os.environ.get("LOG_FORMAT", "text").lower() == "json"
    
    formatter = (
        JSONFormatter()
        if json_format
        else logging.Formatter(
            fmt="%(asctime)s [%(levelname)-8s] %(name)s.%(funcName)s:%(lineno)d — %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z"
        )
    )
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Console handler
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    
    # Suppress noisy third-party loggers
    for noisy in ["urllib3", "asyncio", "multipart", "aiohttp", "uvicorn.access"]:
        logging.getLogger(noisy).setLevel(logging.WARNING)
    
    logging.getLogger(__name__).info(
        f"Logging configured: level={level}, format={'json' if json_format else 'text'}"
    )

