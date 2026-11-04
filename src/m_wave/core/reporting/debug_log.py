# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH
# This tool was created with the help of AI.

"""
DebugLog: the developer's log. Written for developers, not for reviewers.

One file per app launch:
    Development: m-wave/generated/logs/<timestamp>_debug.log
    Production:  exe-folder/logs/<timestamp>_debug.log

Setup (once, in __main__.py, before anything else):
    DebugLog.setup()
    ...
    DebugLog.catch_tk_errors(app)   # after the Tk window exists

NOTE: Do not use f-strings for logging, its faster and more optimized to use
      'idiomatic formatting', logger.info("User %s", user, some_action)

Use anywhere:
    debug = DebugLog()
    debug.info("Loaded %s rows", 1240)
    debug.error("Could not read the sheet", error)   # error = the exception

Every DebugLog() writes to the same file, so you can create one wherever it is
handy. Every line shows the time, level, thread, file, function and line number
of the code that wrote it, so a production log from a bug report points you
straight at the code.

What also ends up here automatically:
    * Every Journal line (copied over by the Journal itself).
    * Every pop-up and question (written by the Notifier).
    * Uncaught crashes on the main thread, worker threads and Tk callbacks.
"""

# stdlib
import logging
import sys
import threading
from datetime import datetime
from pathlib import Path

# local
from m_wave.core.paths import PATHS
from m_wave.core.utils import DATETIME_FORMAT

LOG_FORMAT = (
    "%(asctime)s|%(levelname)-8s|%(threadName)-14s|"
    "%(module)s.%(funcName)s:%(lineno)d|%(message)s"
)
CONSOLE_FORMAT = "%(levelname)-8s|%(module)s:%(lineno)d|%(message)s"

# Keep the newest N debug logs. Older ones are removed when the app starts.
MAX_LOG_FILES = 30

# Third-party libraries that are very chatty at DEBUG level.
QUIET_LIBRARIES = ("PIL", "matplotlib", "reportlab")

_LOGGER_NAME = "m_wave"


class DebugLog:
    """
    A small wrapper around Python's ``logging`` module.

    You never have to touch ``logging`` directly: call ``DebugLog.setup()`` once,
    then use ``debug``, ``info``, ``warning`` and ``error`` on any DebugLog().
    """

    _log_path: Path | None = None  # shared by every DebugLog, set by setup()

    def __init__(self) -> None:
        self._logger = logging.getLogger(_LOGGER_NAME)

    # -------------------------------------------------------------------------
    # Writing
    # -------------------------------------------------------------------------
    def debug(self, msg: str, *args, caller_depth: int = 1) -> None:
        """Fine detail: values, decisions, timings."""
        self._write(logging.DEBUG, msg, args, None, caller_depth)

    def info(self, msg: str, *args, caller_depth: int = 1) -> None:
        """Normal milestones: started, loaded, saved."""
        self._write(logging.INFO, msg, args, None, caller_depth)

    def warning(self, msg: str, *args, caller_depth: int = 1) -> None:
        """Something odd that did not stop the run."""
        self._write(logging.WARNING, msg, args, None, caller_depth)

    def error(
        self,
        msg: str,
        *args,
        error: BaseException | None = None,
        caller_depth: int = 1,
    ) -> None:
        """
        Something went wrong. Pass ``error=`` (the caught exception) and the full
        traceback is written underneath the message.
        """
        self._write(logging.ERROR, msg, args, error, caller_depth)

    def _write(
        self,
        level: int,
        msg: str,
        args: tuple,
        error: BaseException | None,
        caller_depth: int,
    ) -> None:
        # ``caller_depth`` decides which line number is shown in the log.
        #   1 = the code that called debug()/info()/... (the normal case)
        #   2, 3 = further back. Notifier and Journal use these so the log points
        #          at app code instead of at notifier.py or journal.py.
        # +2 skips this method and the public method that called it.
        self._logger.log(
            level,
            msg,
            *args,
            exc_info=error,
            stacklevel=caller_depth + 2,
        )

    # -------------------------------------------------------------------------
    # One-time setup
    # -------------------------------------------------------------------------
    @classmethod
    def setup(cls, console: bool | None = None) -> Path:
        """
        Create today's debug log file. Call once, at the very start of the app.

        console: also print to the terminal. Defaults to on when running from
        source and off in the packaged .exe.

        Returns the path of the log file.
        """
        if cls._log_path is not None:
            return cls._log_path

        log_path = (
            PATHS.logs_dir / f"{datetime.now().strftime(DATETIME_FORMAT)}_debug.log"
        )

        app_logger = logging.getLogger(_LOGGER_NAME)
        app_logger.setLevel(logging.DEBUG)

        # M-WAVE lines are written by the handlers below only. Without this they
        # would also pass up to the root logger and appear twice.
        app_logger.propagate = False

        file_handler = logging.FileHandler(log_path, mode="w", encoding="utf-8")
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        app_logger.addHandler(file_handler)

        if console is None:
            console = not PATHS.is_frozen
        if console:
            console_handler = logging.StreamHandler(sys.stderr)
            console_handler.setFormatter(logging.Formatter(CONSOLE_FORMAT))
            app_logger.addHandler(console_handler)

        # Warnings and errors from third-party libraries also go into the file.
        logging.getLogger().addHandler(file_handler)
        logging.getLogger().setLevel(logging.WARNING)
        for name in QUIET_LIBRARIES:
            logging.getLogger(name).setLevel(logging.WARNING)
        logging.captureWarnings(True)

        cls._log_path = log_path
        cls._catch_crashes()
        cls._delete_old_logs()

        DebugLog().info(
            "Debug log started: %s (packaged exe=%s)", log_path, PATHS.is_frozen
        )
        return log_path

    @classmethod
    def path(cls) -> Path | None:
        """The current debug log file, or None before setup()."""
        return cls._log_path

    @staticmethod
    def catch_tk_errors(root) -> None:
        """
        Tk hides errors raised inside button commands and after() callbacks.
        Call this once with the main window so they are written here instead.
        """
        debug = DebugLog()

        def on_tk_error(exc_type, exc, tb) -> None:
            debug.error("Error in a Tk callback", error=exc)

        root.report_callback_exception = on_tk_error

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------
    @staticmethod
    def _catch_crashes() -> None:
        """Write any uncaught exception (main thread or worker thread) to the log."""
        debug = DebugLog()

        def on_crash(exc_type, exc, tb) -> None:
            if issubclass(exc_type, KeyboardInterrupt):
                sys.__excepthook__(exc_type, exc, tb)
                return
            debug.error("The app crashed", error=exc)

        def on_thread_crash(args: threading.ExceptHookArgs) -> None:
            name = args.thread.name if args.thread else "?"
            debug.error("Thread '%s' crashed", name, error=args.exc_value)

        sys.excepthook = on_crash
        threading.excepthook = on_thread_crash

    @staticmethod
    def _delete_old_logs() -> None:
        logs = sorted(
            PATHS.logs_dir.glob("*_debug.log"), key=lambda p: p.stat().st_mtime
        )
        for old_log in logs[:-MAX_LOG_FILES]:
            try:
                old_log.unlink()
            except OSError:
                pass
