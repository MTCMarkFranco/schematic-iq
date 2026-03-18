"""
Structured JSON-line logger for the schematic-iq pipeline.

Emits log records as JSON lines to stdout (or configurable stream).
Falls back gracefully to Python's standard logging when structured
output is not needed.

Usage:
    from services.telemetry import get_logger, configure_logging

    configure_logging(level="INFO", json_output=True)
    log = get_logger("stage1")
    log.info("geometry_done", wires=42, chains=8, elapsed=1.23)
"""

import json
import logging
import sys
import time
from typing import Any


class _JsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        # Merge any extra structured fields attached by StructuredLogger
        extras = getattr(record, "_structured", None)
        if extras:
            payload.update(extras)
        return json.dumps(payload, default=str)


class StructuredLogger:
    """Thin wrapper around stdlib logger that attaches keyword fields."""

    def __init__(self, logger: logging.Logger):
        self._logger = logger

    # Delegate standard levels ------------------------------------------------
    def debug(self, msg: str, **kw: Any) -> None:
        self._log(logging.DEBUG, msg, kw)

    def info(self, msg: str, **kw: Any) -> None:
        self._log(logging.INFO, msg, kw)

    def warning(self, msg: str, **kw: Any) -> None:
        self._log(logging.WARNING, msg, kw)

    def error(self, msg: str, **kw: Any) -> None:
        self._log(logging.ERROR, msg, kw)

    # Internal ----------------------------------------------------------------
    def _log(self, level: int, msg: str, extras: dict[str, Any]) -> None:
        if not self._logger.isEnabledFor(level):
            return
        record = self._logger.makeRecord(
            self._logger.name,
            level,
            "(telemetry)",
            0,
            msg,
            (),
            None,
        )
        record._structured = extras  # type: ignore[attr-defined]
        self._logger.handle(record)


_configured = False


def configure_logging(
    level: str = "WARNING",
    json_output: bool = False,
    stream: Any = None,
) -> None:
    """Configure the root ``siq`` logger hierarchy.

    Parameters
    ----------
    level : str
        Python log level name (DEBUG, INFO, WARNING, ERROR).
    json_output : bool
        If True, emit JSON lines. Otherwise use a simple text format.
    stream :
        Output stream (defaults to sys.stdout).
    """
    global _configured
    root = logging.getLogger("siq")
    root.setLevel(getattr(logging, level.upper(), logging.WARNING))

    # Remove previous handlers to allow re-configuration
    root.handlers.clear()

    handler = logging.StreamHandler(stream or sys.stdout)
    if json_output:
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)-5s [%(name)s] %(message)s")
        )
    root.addHandler(handler)
    _configured = True


def get_logger(name: str) -> StructuredLogger:
    """Return a structured logger under the ``siq`` namespace.

    If ``configure_logging`` has not been called, the logger will be
    effectively silent (WARNING level, no handler on ``siq`` root)
    so the pipeline's existing Rich output is unaffected.
    """
    return StructuredLogger(logging.getLogger(f"siq.{name}"))
