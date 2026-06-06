"""Thread-safe logging: rotating file + optional QueueHandler for the UI."""
from __future__ import annotations

import logging
import queue
import sys
import tempfile
from logging.handlers import QueueHandler, RotatingFileHandler
from pathlib import Path

_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(threadName)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_initialized = False


class _UiQueueHandler(QueueHandler):
    """Pushes formatted records onto a shared queue for the wizard's install page."""

    def __init__(self, ui_queue: queue.Queue) -> None:
        super().__init__(ui_queue)
        self.setFormatter(logging.Formatter(_LOG_FORMAT, _DATE_FORMAT))

    def emit(self, record: logging.LogRecord) -> None:  # type: ignore[override]
        try:
            msg = self.format(record)
            self.queue.put(("log", msg))
        except Exception:
            self.handleError(record)


def _resolve_app_name() -> str:
    try:
        if getattr(sys, "frozen", False):
            return Path(sys.executable).stem
    except OSError:
        pass
    return "EchoesVulkanHelper"


def _attach_file_handler(log_dir: Path) -> None:
    global _initialized
    root = logging.getLogger()
    log_file = log_dir / "install.log"
    file_handler = RotatingFileHandler(
        log_file, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter(_LOG_FORMAT, _DATE_FORMAT))
    root.addHandler(file_handler)
    _initialized = True
    root.info("Logging initialized at %s", log_file)


def setup_logging(log_dir: Path) -> logging.Logger:
    """Configure the root logger with a rotating file + stdout handler.

    Idempotent. On PermissionError for the primary log dir, falls back to a
    per-temp directory so logging still works on locked-down systems.
    """
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    if _initialized:
        return root

    for h in list(root.handlers):
        root.removeHandler(h)

    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        _attach_file_handler(log_dir)
    except OSError as exc:
        app_name = _resolve_app_name()
        fallback = Path(tempfile.gettempdir()) / app_name / "logs"
        fallback.mkdir(parents=True, exist_ok=True)
        stream = logging.StreamHandler()
        stream.setFormatter(logging.Formatter(_LOG_FORMAT, _DATE_FORMAT))
        root.addHandler(stream)
        root.warning(
            "Could not open log file in %s (%s); using temp fallback %s",
            log_dir, exc, fallback,
        )
        try:
            _attach_file_handler(fallback)
        except OSError as exc2:
            root.warning("Could not open fallback log file (%s); stdout only", exc2)

    return root


def attach_ui_queue(ui_queue: queue.Queue) -> None:
    """Attach a queue handler so the install page can render logs live."""
    root = logging.getLogger()
    for h in list(root.handlers):
        if isinstance(h, _UiQueueHandler):
            root.removeHandler(h)
    root.addHandler(_UiQueueHandler(ui_queue))


def detach_ui_queue() -> None:
    root = logging.getLogger()
    for h in list(root.handlers):
        if isinstance(h, _UiQueueHandler):
            root.removeHandler(h)
