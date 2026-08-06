from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone

_STANDARD_LOG_RECORD_FIELDS = set(logging.makeLogRecord({}).__dict__) | {
    "message",
    "asctime",
}


class JsonLogFormatter(logging.Formatter):
    """Minimal dependency-free JSON formatter for ECS/CloudWatch logs."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        payload.update(
            {
                key: value
                for key, value in record.__dict__.items()
                if key not in _STANDARD_LOG_RECORD_FIELDS and not key.startswith("_")
            }
        )
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            default=str,
        )


def setup_logging(level: int | str | None = None) -> None:
    """Configure local text logs or deployment-friendly JSON logs.

    Environment variables:
      ``LOG_LEVEL``: DEBUG, INFO, WARNING, ERROR (default INFO)
      ``LOG_FORMAT``: ``text`` or ``json`` (default text)
    """
    resolved_level = level or os.getenv("LOG_LEVEL", "INFO").upper()
    log_format = os.getenv("LOG_FORMAT", "text").lower()
    formatter: logging.Formatter
    if log_format == "json":
        formatter = JsonLogFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        root.addHandler(handler)
    elif log_format == "json":
        # Uvicorn installs handlers before importing the ASGI app. Reformat
        # those handlers so application and server logs remain machine-readable
        # in ECS/CloudWatch without adding duplicate output streams.
        for handler in root.handlers:
            handler.setFormatter(formatter)
    root.setLevel(resolved_level)

    for noisy_logger in (
        "httpx",
        "httpcore",
        "google",
        "openai",
        "urllib3",
    ):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)
