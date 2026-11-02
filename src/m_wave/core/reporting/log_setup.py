# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH
# This tool was created with the help of AI.

# stdlib
import logging
import os
import sys
import threading
from datetime import datetime
from pathlib import Path

# local
from m_wave.core.paths import PATHS
from m_wave.core.reporting.run_log import is_decorative
from m_wave.core.utils import DATETIME_FORMAT

# %(name)s is the logger ("m_wave.run" for run-log lines), %(module)s is the file
# that made the call, so both are shown.
DEV_LOG_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(threadName)-12s | %(run_id)s | "
    "%(name)s | %(module)s.%(funcName)s:%(lineno)d | %(message)s"
)
CONSOLE_LOG_FORMAT = "%(levelname)-8s %(module)s:%(lineno)d | %(message)s"

# Set M_WAVE_DEBUG=1 to get console output in a frozen (production) build, or
# M_WAVE_LOG_LEVEL=INFO to quieten the developer log file.
_ENV_DEBUG = "M_WAVE_DEBUG"
_ENV_LEVEL = "M_WAVE_LOG_LEVEL"

# Keep the newest N developer logs, older ones are removed at startup.
MAX_DEV_LOG_FILES = 30

# Third-party loggers that are noisy at DEBUG level.
_QUIET_LOGGERS = ("PIL", "matplotlib", "reportlab")

# RUN ID Tagging
_active_run_id = ""


def set_active_run_id(run_id: str | None = None) -> None:
    """
    Tag every following log record with 'run_id' or '-' when None.
    """
    global _active_run_id
    _active_run_id = run_id or "-"


class RunIdFilter(logging.Filter):
    """
    Adds 'record.run_id' so formatters can reference the run id.
    Also drops pure layout records form the dev log.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if is_decorative(record):
            return False
        if not hasattr(record, "run_id"):
            record.run_id = _active_run_id
        return True


# SETUP
_configured = False


def _resolve_level() -> int:
    name = os.environ.get(_ENV_LEVEL, "DEBUG").upper()
    return getattr(logging, name, logging.DEBUG)


def _prune_old_logs(log_dir: Path, keep: int) -> None:
    logs = sorted(log_dir.glob("*_dev.log"), key=lambda p: p.stat().st_mtime)
    for old in logs[:-keep] if keep > 0 else []:
        try:
            old.unlink()
        except OSError:
            pass


def _install_exception_hooks() -> None:
    """
    Route uncaught exceptions into the dev log.
    """
    dev_logger = logging.getLogger("m_wave.uncaught")

    def _sys_hook(exc_type, exc, tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc, tb)
            return
        dev_logger.critical("Uncaught excpetion", exc_info=(exc_type, exc, tb))

    def _thread_hook(args: threading.ExceptHookArgs):
        dev_logger.critical(
            "Uncaught exception in thread %s",
            args.thread.name if args.thread else "?",
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    sys.excepthook = _sys_hook
    threading.excepthook = _thread_hook


def install_tk_exception_hook(root) -> None:
    """
    Tk swallows exceptions raised in callbacks (buttons, after())
    Call this once with the root window so they reach the dev log.
    """
    dev_logger = logging.getLogger("m_wave.uncaught.tk")

    def _report_callback_exception(exc_type, exc, tb):
        dev_logger.error("Exception in Tk callback", exc_info=(exc_type, exc, tb))


def configure_logging(console: bool | None = None) -> Path:
    """
    Configures the root logger with the dev log file handler.

    console: force the console handler on/off. Defaults to on when running from source,
    off in a frozen build unless M_WAVE_DEBUG =1.

    Returns the dev log path.
    """
    global _configured

    log_dir = PATHS.logs_dir
    log_path = log_dir / f"{datetime.now().strftime(DATETIME_FORMAT)}_dev.log"

    if _configured:
        return log_path

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    run_id_filter = RunIdFilter()

    file_handler = logging.FileHandler(log_path, mode="w", encoding="utf-8")
    file_handler.setLevel(_resolve_level())
    file_handler.setFormatter(logging.Formatter(DEV_LOG_FORMAT))
    file_handler.addFilter(run_id_filter)

    if console is None:
        console = (not PATHS.is_frozen) or os.environ.get(_ENV_DEBUG) == "1"
    if console:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(logging.Formatter(CONSOLE_LOG_FORMAT))
        console_handler.addFilter(run_id_filter)
        root.addHandler(console_handler)

    for name in _QUIET_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)

    logging.captureWarnings(True)
    _install_exception_hooks()
    _prune_old_logs(log_dir, MAX_DEV_LOG_FILES)

    _configured = True
    logging.getLogger(__name__).info(
        "Developer log started %s (frozen=%s)", log_path, PATHS.is_frozen
    )

    return log_path
