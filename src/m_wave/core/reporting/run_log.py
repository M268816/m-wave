# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH
# This tool was created with the help of AI.

"""
The TECHNICAL run log: a step-by-step record of a single process run, written for
technical reviewers and non-matching comparison investigations.

    run = RunLog()
    run.title("Extraction")
    run.info("Read 1,204 rows from MTL.")
    run.warning("3 rows had blank keys and were skipped.")

How it works
------------
``RunLog`` is a thin wrapper over the standard ``logging`` logger named
``m_wave.run``. It does not store or write anything itself. Handlers decide where
records go:

    * ``RunSession`` attaches a FileHandler -> <run folder>/run.log
    * ``attach_display()`` attaches a handler -> the GUI ScrolledText
    * The logger propagates to the root logger -> the developer log

Headings and dividers are normal records tagged with ``m_wave_kind``. The
``RunLogFormatter`` draws the boxes, so the developer log only shows the plain text.

Rule of thumb
-------------
    * Technical reviewer needs it?  -> run.info / run.warning / run.error
    * Only useful to you debugging? -> logger.debug in that module
    * Non-technical reviewer?       -> a field on the PDF template
    * User must see/answer it now?  -> Notifier
"""

from __future__ import annotations

# stdlib
import logging
import queue
import textwrap
from datetime import datetime
from pathlib import Path
from tkinter import TclError
from typing import TYPE_CHECKING

# local
from m_wave.core.utils import DATETIME_FORMAT_MERCK

if TYPE_CHECKING:
    from ttkbootstrap.widgets.scrolled import ScrolledText

RUN_LOGGER_NAME = "m_wave.run"
DEFAULT_WIDTH = 88

# Record "kinds" understood by RunLogFormatter. Anything else is a plain line.
KIND_ATTR = "m_wave_kind"
TITLE_ATTR = "m_wave_title"
LABEL_ATTR = "m_wave_label"

TITLE = "title"
SUBTITLE = "subtitle"
SIMPLE_TITLE = "simple_title"
DIVIDER = "divider"
SEPARATOR = "separator"
SECTION = "section"
ERROR_HIGHLIGHT = "error_highlight"
ERROR_TITLED = "error_titled"
ERROR_DIVIDER = "error_divider"
ERROR_SEPARATOR = "error_separator"
ERROR_SECTION = "error_section"

# Records that carry no information, only layout. The developer log drops these.
DECORATIVE_KINDS = frozenset(
    {DIVIDER, SEPARATOR, SECTION, ERROR_DIVIDER, ERROR_SEPARATOR, ERROR_SECTION}
)

_LABEL_WIDTH = len("EXCEPTION")
_PREFIX_MARK = "❚┋❚ "


def is_decorative(record: logging.LogRecord) -> bool:
    return getattr(record, KIND_ATTR, None) in DECORATIVE_KINDS


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------
class RunLogFormatter(logging.Formatter):
    """
    Renders run-log records as fixed-width text.

    show_timestamps / show_levels add the "<time> <LEVEL> ❚┋❚ " prefix.
    show_traceback adds the full traceback for exceptions; otherwise only the
    exception type and message are shown (the traceback is always in the
    developer log).
    """

    def __init__(
        self,
        width: int = DEFAULT_WIDTH,
        show_timestamps: bool = True,
        show_levels: bool = True,
        show_traceback: bool = False,
    ) -> None:
        super().__init__()
        self.width = width
        self.show_timestamps = show_timestamps
        self.show_levels = show_levels
        self.show_traceback = show_traceback

    # -- body ---------------------------------------------------------------
    def _render_body(self, record: logging.LogRecord) -> list[str]:
        kind = getattr(record, KIND_ATTR, None)
        msg = record.getMessage()
        w = self.width
        inner = w - 4

        if kind == TITLE:
            return [
                f"╔{'═' * (w - 2)}╗",
                f"║ {msg.center(inner)} ║",
                f"╚{'═' * (w - 2)}╝",
            ]
        if kind == SUBTITLE:
            return [
                f"┌{'─' * (w - 2)}┐",
                f"│ {msg.center(inner)} │",
                f"└{'─' * (w - 2)}┘",
            ]
        if kind == SIMPLE_TITLE:
            space = max(0, w - 2 - len(msg))
            left, right = space // 2, space - space // 2
            return [f"{'─' * left} {msg} {'─' * right}"]
        if kind == DIVIDER:
            return ["═" * w]
        if kind in (SEPARATOR, SECTION):
            return ["─" * w]
        if kind == ERROR_DIVIDER:
            return ["#" * w]
        if kind == ERROR_SEPARATOR:
            return ["+" * w]
        if kind == ERROR_SECTION:
            return ["~" * w]
        if kind == ERROR_HIGHLIGHT:
            label = f" {msg} "
            if len(label) > w - 2:
                label = label[: max(0, w - 5)] + "..."
            space = w - 2 - len(label)
            left, right = space // 2, space - space // 2
            return ["X" + "=" * left + label + "=" * right + "X"]
        if kind == ERROR_TITLED:
            title = str(getattr(record, TITLE_ATTR, "")).upper()
            return [
                f"X{'═' * (w - 2)}X",
                f"║ {title.center(inner)} ║",
                f"╠{'═' * (w - 2)}╣",
                f"║ {msg.center(inner)} ║",
                f"X{'═' * (w - 2)}X",
            ]

        # Plain message: keep the author's line breaks, wrap long lines.
        lines: list[str] = []
        for raw in msg.splitlines() or [""]:
            lines.extend(textwrap.wrap(raw, width=w) or [""])
        return lines

    def _render_exception(self, record: logging.LogRecord) -> list[str]:
        if not record.exc_info or record.exc_info[0] is None:
            return []
        if self.show_traceback:
            return self.formatException(record.exc_info).splitlines()
        exc_type, exc, _ = record.exc_info
        return [f"  -> {exc_type.__name__}: {exc}"]

    # -- prefix -------------------------------------------------------------
    def _prefix(self, record: logging.LogRecord) -> str:
        prefix = ""
        if self.show_timestamps:
            moment = datetime.fromtimestamp(record.created)
            prefix += moment.strftime(DATETIME_FORMAT_MERCK) + " "
        if self.show_levels:
            label = getattr(record, LABEL_ATTR, None) or record.levelname
            prefix += f"{label:<{_LABEL_WIDTH}} {_PREFIX_MARK}"
        return prefix

    def format(self, record: logging.LogRecord) -> str:
        lines = self._render_body(record) + self._render_exception(record)
        prefix = self._prefix(record)
        indent = " " * len(prefix)
        return "\n".join(
            (prefix if i == 0 else indent) + line for i, line in enumerate(lines)
        )


# ---------------------------------------------------------------------------
# GUI display handler
# ---------------------------------------------------------------------------
class TextDisplayHandler(logging.Handler):
    """
    Sends formatted run-log records to a ttkbootstrap ScrolledText.

    Thread-safe: ``emit`` only puts text in a queue. The Tk main thread drains the
    queue with ``after()``, so worker threads never touch Tk widgets.
    """

    POLL_MS = 50

    def __init__(self, text_display: ScrolledText) -> None:
        super().__init__(level=logging.INFO)
        self.text_display = text_display
        self._queue: queue.SimpleQueue[str] = queue.SimpleQueue()
        self._closed = False
        # Must be called from the Tk main thread (GUI build / start_process).
        self.text_display.after(self.POLL_MS, self._drain)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._queue.put(self.format(record))
        except Exception:
            self.handleError(record)

    def _drain(self) -> None:
        if self._closed:
            return
        try:
            tw = self.text_display.text  # the inner tk.Text widget
            pending = []
            while True:
                try:
                    pending.append(self._queue.get_nowait())
                except queue.Empty:
                    break
            if pending:
                tw.configure(state="normal")
                tw.insert("end", "\n".join(pending) + "\n")
                tw.configure(state="disabled")
                tw.see("end")
            self.text_display.after(self.POLL_MS, self._drain)
        except TclError:
            # Widget was destroyed (frame closed). Stop polling quietly.
            self._closed = True

    def close(self) -> None:
        self._closed = True
        super().close()


# Only one ScrolledText is active at a time (one WavePack frame is shown).
_display_handler: TextDisplayHandler | None = None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
class RunLog:
    """
    Writes to the technical run log. See the module docstring.

    All methods accept ``stacklevel`` so wrappers (like the legacy ``Reporting``
    class) can make the developer log point at the real caller.
    """

    def __init__(self, name: str = RUN_LOGGER_NAME, width: int = DEFAULT_WIDTH) -> None:
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        self.width = width

    # -- core ---------------------------------------------------------------
    def _log(
        self,
        level: int,
        msg: str,
        *,
        kind: str | None = None,
        label: str | None = None,
        title: str | None = None,
        exc_info: bool = False,
        stacklevel: int = 1,
    ) -> None:
        extra = {KIND_ATTR: kind, LABEL_ATTR: label, TITLE_ATTR: title}
        # +2: skip _log and the public method so the record points at the caller.
        self.logger.log(
            level, msg, exc_info=exc_info, extra=extra, stacklevel=stacklevel + 2
        )

    # -- levels -------------------------------------------------------------
    def debug(self, msg: str, stacklevel: int = 1) -> None:
        """Run-related detail. Goes to the developer log only (run.log is INFO+)."""
        self._log(logging.DEBUG, msg, stacklevel=stacklevel)

    def info(self, msg: str, stacklevel: int = 1) -> None:
        self._log(logging.INFO, msg, stacklevel=stacklevel)

    def warning(self, msg: str, stacklevel: int = 1) -> None:
        self._log(logging.WARNING, msg, stacklevel=stacklevel)

    def error(self, msg: str, stacklevel: int = 1) -> None:
        self._log(logging.ERROR, msg, stacklevel=stacklevel)

    def critical(self, msg: str, stacklevel: int = 1) -> None:
        self._log(logging.CRITICAL, msg, stacklevel=stacklevel)

    def exception(self, msg: str, stacklevel: int = 1) -> None:
        """Call from inside an ``except`` block. Traceback goes to the dev log."""
        self._log(
            logging.ERROR, msg, label="EXCEPTION", exc_info=True, stacklevel=stacklevel
        )

    def question(self, msg: str, stacklevel: int = 1) -> None:
        """Record a question put to the user (the Notifier shows it)."""
        self._log(logging.INFO, msg, label="QUESTION", stacklevel=stacklevel)

    def answer(self, msg: str, stacklevel: int = 1) -> None:
        """Record the user's answer to a question."""
        self._log(logging.INFO, msg, label="ANSWER", stacklevel=stacklevel)

    # -- headings and dividers ----------------------------------------------
    def title(self, msg: str, stacklevel: int = 1) -> None:
        self._log(logging.INFO, msg, kind=TITLE, stacklevel=stacklevel)

    def subtitle(self, msg: str, stacklevel: int = 1) -> None:
        self._log(logging.INFO, msg, kind=SUBTITLE, stacklevel=stacklevel)

    def simple_title(self, msg: str, stacklevel: int = 1) -> None:
        self._log(logging.INFO, msg, kind=SIMPLE_TITLE, stacklevel=stacklevel)

    def divider(self, stacklevel: int = 1) -> None:
        self._log(logging.INFO, "", kind=DIVIDER, stacklevel=stacklevel)

    def separator(self, stacklevel: int = 1) -> None:
        self._log(logging.INFO, "", kind=SEPARATOR, stacklevel=stacklevel)

    def section(self, stacklevel: int = 1) -> None:
        self._log(logging.INFO, "", kind=SECTION, stacklevel=stacklevel)

    def highlight_error(
        self, msg: str, is_critical: bool = False, stacklevel: int = 1
    ) -> None:
        level = logging.CRITICAL if is_critical else logging.ERROR
        self._log(level, msg, kind=ERROR_HIGHLIGHT, stacklevel=stacklevel)

    def highlight_titled_error(
        self,
        msg: str,
        title: str = "COMPARISON FAILED",
        is_critical: bool = False,
        stacklevel: int = 1,
    ) -> None:
        level = logging.CRITICAL if is_critical else logging.ERROR
        self._log(level, msg, kind=ERROR_TITLED, title=title, stacklevel=stacklevel)

    def error_divider(self, stacklevel: int = 1) -> None:
        self._log(logging.ERROR, "", kind=ERROR_DIVIDER, stacklevel=stacklevel)

    def error_separator(self, stacklevel: int = 1) -> None:
        self._log(logging.ERROR, "", kind=ERROR_SEPARATOR, stacklevel=stacklevel)

    def error_section(self, stacklevel: int = 1) -> None:
        self._log(logging.ERROR, "", kind=ERROR_SECTION, stacklevel=stacklevel)

    # -- handler management -------------------------------------------------
    def attach_file(self, path: Path) -> logging.Handler:
        """
        Start writing this run to ``path``. Records are flushed as they arrive, so
        the file survives a crash. Always timestamped, regardless of user prefs.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(path, mode="w", encoding="utf-8")
        handler.setLevel(logging.INFO)
        handler.setFormatter(
            RunLogFormatter(self.width, show_timestamps=True, show_levels=True)
        )
        self.logger.addHandler(handler)
        return handler

    def detach(self, handler: logging.Handler | None) -> None:
        if handler is None:
            return
        self.logger.removeHandler(handler)
        handler.close()

    def attach_display(
        self,
        text_display: ScrolledText,
        show_timestamps: bool = False,
        show_levels: bool = False,
    ) -> None:
        """
        Mirror the run log into a ScrolledText. Replaces any previous display.
        Call from the Tk main thread. The user preferences only affect this
        display; run.log always has timestamps and levels.
        """
        global _display_handler
        if _display_handler is not None:
            self.logger.removeHandler(_display_handler)
            _display_handler.close()
        handler = TextDisplayHandler(text_display)
        handler.setFormatter(
            RunLogFormatter(
                self.width, show_timestamps=show_timestamps, show_levels=show_levels
            )
        )
        self.logger.addHandler(handler)
        _display_handler = handler
