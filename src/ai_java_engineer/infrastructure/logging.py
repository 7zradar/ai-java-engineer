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


class StructuredLoggerAdapter:
    """Fallback adapter for standard logging allowing key-value kwargs like structlog."""

    def __init__(self, logger: logging.Logger):
        self._logger = logger

    def _format_msg(self, msg: str, kwargs: dict[str, Any]) -> str:
        if kwargs:
            extra = " ".join(f"{k}={v}" for k, v in kwargs.items())
            return f"{msg} | {extra}"
        return msg

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._logger.info(self._format_msg(msg, kwargs), *args)

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._logger.warning(self._format_msg(msg, kwargs), *args)

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._logger.error(self._format_msg(msg, kwargs), *args)

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._logger.debug(self._format_msg(msg, kwargs), *args)

    def critical(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._logger.critical(self._format_msg(msg, kwargs), *args)


def get_logger(name: str) -> Any:
    """Returns a structured logger if available, otherwise wrapped standard logger."""
    if HAS_STRUCTLOG:
        return structlog.get_logger(name)
    return StructuredLoggerAdapter(logging.getLogger(name))
