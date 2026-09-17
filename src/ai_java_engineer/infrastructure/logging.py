"""Structured logging configuration for AI Java Engineer."""

import logging
import sys
from typing import Any

try:
    import structlog

    HAS_STRUCTLOG = True
except ImportError:
    HAS_STRUCTLOG = False


def configure_logging(log_level: str = "INFO", json_format: bool = False) -> None:
    """Configures structured logging for the application."""
    level = getattr(logging, log_level.upper(), logging.INFO)

    if HAS_STRUCTLOG and json_format:
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.processors.add_log_level,
                structlog.processors.StackInfoRenderer(),
                structlog.dev.set_exc_info,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(level),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
            cache_logger_on_first_use=True,
        )
    else:
        logging.basicConfig(
            level=level,
            format="%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s",
            stream=sys.stdout,
            force=True,
        )


def get_logger(name: str) -> Any:
    """Returns a structured logger if available, otherwise standard logging logger."""
    if HAS_STRUCTLOG:
        return structlog.get_logger(name)
    return logging.getLogger(name)
