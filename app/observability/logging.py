import json
import logging
import sys
from typing import Any

from app.core.config import get_settings

LOGGER_NAME = "local_ai_research_assistant"


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        context = getattr(record, "context", None)
        if isinstance(context, dict):
            payload.update({key: value for key, value in context.items() if value is not None})
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging() -> None:
    settings = get_settings()
    logger = logging.getLogger(LOGGER_NAME)
    logger.handlers.clear()
    logger.setLevel(settings.log_level.upper())

    handler: logging.Handler
    if settings.log_file:
        handler = logging.FileHandler(settings.log_file, encoding="utf-8")
    else:
        handler = logging.StreamHandler(sys.stdout)

    if settings.log_format.lower() == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(levelname)s %(name)s %(message)s %(context)s"))
    logger.addHandler(handler)
    logger.propagate = False


def get_logger() -> logging.Logger:
    return logging.getLogger(LOGGER_NAME)


def log_event(level: int, message: str, **context: Any) -> None:
    get_logger().log(level, message, extra={"context": context})
