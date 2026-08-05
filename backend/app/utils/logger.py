"""Structured logging with in-memory log buffer for API access."""
import logging
import queue
import threading
from datetime import datetime, timezone
from typing import Optional
import structlog

# In-memory circular log buffer (last 1000 entries)
_log_buffer: list[dict] = []
_log_lock = threading.Lock()
MAX_LOG_ENTRIES = 1000


def _add_to_buffer(level: str, message: str, job_id: Optional[str] = None,
                   stage: Optional[str] = None, extra: Optional[dict] = None) -> None:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "message": message,
        "job_id": job_id,
        "stage": stage,
        "extra": extra or {},
    }
    with _log_lock:
        _log_buffer.append(entry)
        if len(_log_buffer) > MAX_LOG_ENTRIES:
            _log_buffer.pop(0)


def get_logs(limit: int = 100, level: Optional[str] = None,
             job_id: Optional[str] = None) -> list[dict]:
    """Return recent log entries from the in-memory buffer."""
    with _log_lock:
        entries = list(_log_buffer)

    if level:
        entries = [e for e in entries if e["level"] == level]
    if job_id:
        entries = [e for e in entries if e["job_id"] == job_id]

    return entries[-limit:]


class BufferingHandler(logging.Handler):
    """Custom logging handler that writes to the in-memory buffer."""

    LEVEL_MAP = {
        logging.DEBUG: "debug",
        logging.INFO: "info",
        logging.WARNING: "warning",
        logging.ERROR: "error",
        logging.CRITICAL: "critical",
    }

    def emit(self, record: logging.LogRecord) -> None:
        level = self.LEVEL_MAP.get(record.levelno, "info")
        job_id = getattr(record, "job_id", None)
        stage = getattr(record, "stage", None)
        _add_to_buffer(level=level, message=self.format(record),
                       job_id=job_id, stage=stage)


def setup_logging() -> None:
    """Configure structured logging for the application."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )

    # Also wire into stdlib logging for compatibility
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    buffering_handler = BufferingHandler()
    buffering_handler.setFormatter(logging.Formatter("%(message)s"))
    root_logger.addHandler(buffering_handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    root_logger.addHandler(console_handler)


def get_logger(name: str):
    """Get a structlog logger."""
    return structlog.get_logger(name)


def log_to_buffer(level: str, message: str, job_id: Optional[str] = None,
                  stage: Optional[str] = None, **kwargs) -> None:
    """Directly add a log entry to the buffer."""
    _add_to_buffer(level=level, message=message, job_id=job_id,
                   stage=stage, extra=kwargs)
