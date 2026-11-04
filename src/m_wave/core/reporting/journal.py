# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH
# This tool was created with the help of AI.

"""
Journal: the technical record of a process run, written for technical reviewers
and investigating comparisons that did not match.

    journal.title("Comparing workbooks")
    journal.info("Read 1,240 rows from File 1.")
    journal.warning("3 rows had a blank key and were skipped.")
    journal.error("12 rows did not match. See mismatches.csv.")

Each line goes to three places:
    1. journal.log in the run folder     (always with time and level)
    2. the GUI text box, if one is shown (time and level follow user preferences)
    3. the DebugLog                      (so your debug log tells the full story)

Between runs there is no journal.log open. Lines still reach the GUI and the
DebugLog, so nothing is lost.

Example journal.log line:
    03-Nov-2026|14:02:11|INFO      ┋ Read 1,240 rows from File 1.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ttkbootstrap.widgets.scrolled import ScrolledText


# stdlib
import queue
import textwrap
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tkinter import TclError
from typing import TextIO

# local
from m_wave.core.reporting.debug_log import DebugLog
from m_wave.core.utils import DATETIME_FORMAT_MERCK

WIDTH = 88  # characters per line, journal character width
LEVEL_WIDTH = len("QUESTION")  # padding for debug level text in the logs.
MARK = "┋ "  # special decoration prefix for logging messages


@dataclass
class JournalEntry:
    """
    One entry written to the journal. A list[str] of text.
    Uses debug levels: ``INFO``,``WARNING``,``ERROR``,``QUESTION``,``ANSWER``
    NOTE: A title box is one entry with 3 lines.
    """

    time: datetime
    level: str
    lines: list[str]


def format_entry(entry: JournalEntry, show_time: bool, show_level: bool) -> str:
    """
    Turn an entry into text. The first line gets the timestamp/debug level prefix, the
    following lines are indented to line up underneath it.
    """
    prefix = ""
    if show_time:
        prefix += entry.time.strftime(DATETIME_FORMAT_MERCK) + "|"
    if show_level:
        prefix += f"{entry.level:<{LEVEL_WIDTH}}|{MARK}"

    indent = " " * len(prefix)
    text_lines = [
        (prefix if number == 0 else indent) + line
        for number, line in enumerate(entry.lines)
    ]
    return "\n".join(text_lines)


def wrap(text: str, width: int = WIDTH) -> list[str]:
    """Keep the line breaks in ``text``, and wrap any line longer than ``width``."""
    lines: list[str] = []
    for line in text.splitlines() or [""]:
        lines.extend(textwrap.wrap(line, width=width) or [""])
    return lines


# Box drawing for headings
def title_box(text: str, width: int = WIDTH) -> list[str]:
    return [
        "╔" + "═" * (width - 2) + "╗",
        "║ " + text.center(width - 4) + " ║",
        "╚" + "═" * (width - 2) + "╝",
    ]


def subtitle_box(text: str, width: int = WIDTH) -> list[str]:
    return [
        "┌" + "─" * (width - 2) + "┐",
        "│ " + text.center(width - 4) + " │",
        "└" + "─" * (width - 2) + "┘",
    ]


def heading_line(text: str, width: int = WIDTH) -> list[str]:
    return [f" {text} ".center(width, "─")]


def error_banner_line(text: str, width: int = WIDTH) -> list[str]:
    return ["X" + f" {text.upper()} ".center(width - 2, "=") + "X"]


# GUI display bootstrap for ScrolledText objects
class JournalDisplay:
    """
    Shows journal entries in a ttkbootstrap ScrolledText.

    Tk widgets may only be touched from the main thread, but the journal is
    written from the worker thread. So entries are put in a queue, and the main
    thread checks the queue every 50 ms (with ``after``) and adds the text.

    Create this on the main thread (it starts the 50 ms check).
    """

    CHECK_EVERY_MS = 50

    def __init__(
        self, text_box: ScrolledText, show_time: bool, show_level: bool
    ) -> None:
        self.text_box = text_box
        self.show_time = show_time
        self.show_level = show_level
        self._waiting: queue.SimpleQueue[JournalEntry] = queue.SimpleQueue()
        self._stopped = False
        self.text_box.after(self.CHECK_EVERY_MS, self._add_waiting_entries)

    def add(self, entry: JournalEntry) -> None:
        """Safe to call from any thread."""
        self._waiting.put(entry)

    def stop(self) -> None:
        self._stopped = True

    def _add_waiting_entries(self) -> None:
        """Runs on the main thread every CHECK_EVERY_MS ms."""
        if self._stopped:
            return

        texts: list[str] = []
        while not self._waiting.empty():
            entry = self._waiting.get()
            texts.append(format_entry(entry, self.show_time, self.show_level))

        try:
            if texts:
                widget = self.text_box.text  # the tk.Text inside the ScrolledText
                widget.configure(state="normal")
                widget.insert("end", "\n".join(texts) + "\n")
                widget.configure(state="disabled")
                widget.see("end")
            self.text_box.after(self.CHECK_EVERY_MS, self._add_waiting_entries)
        except TclError:
            # The text box was destroyed (WavePack closed). Stop checking.
            self._stopped = True


# -----------------------------------------------------------------------------
# The Journal
# -----------------------------------------------------------------------------
class Journal:
    """
    Writes the technical journal. See the top of this file for where lines go.

    The Reporter calls ``open_file`` when a run starts and ``close_file`` when it
    finishes. Your processor only uses the writing methods.
    """

    def __init__(self) -> None:
        self.file_path: Path | None = None
        self.display: JournalDisplay | None = None
        self._file: TextIO | None = None
        self._lock = threading.Lock()  # main and worker thread lockout
        self._debug = DebugLog()

    def info(self, text: str) -> None:
        """
        General informational journal entry.
        """
        self._write("INFO", wrap(text), text)

    def warning(self, text: str) -> None:
        """
        Warning informational journal entry.
        """
        self._write("WARNING", wrap(text), text)

    def error(self, text: str) -> None:
        """
        A problematic informational journal entry a techical reviewer must know about.
        The journal only gets this message; a full traceback should be sent to the
        DebugLog.
        """
        self._write("ERROR", wrap(text), text)

    def question(self, text: str) -> None:
        """Written by the Notifier when it asks the user something."""
        self._write("QUESTION", wrap(text), text)

    def answer(self, text: str) -> None:
        """Written by the Notifier with the user's answer."""
        self._write("ANSWER", wrap(text), text)

    def title(self, text: str) -> None:
        """Double-line box. Use once per run or per major stage."""
        self._write("INFO", title_box(text), text)

    def subtitle(self, text: str) -> None:
        """Single-line box."""
        self._write("INFO", subtitle_box(text), text)

    def heading(self, text: str) -> None:
        """──── text ──── Use for steps inside a stage."""
        self._write("INFO", heading_line(text), text)

    def divider(self) -> None:
        """═════ A plain line. Not copied to the DebugLog."""
        self._write("INFO", ["═" * WIDTH], debug_text=None)

    def error_banner(self, text: str) -> None:
        """X===== TEXT =====X Makes a failure easy to find when scrolling."""
        self._write("ERROR", error_banner_line(text), text)

    def open_file(self, file_path: Path) -> None:
        """
        Used by the Reporter.
        Start writing to ``file_path`` (the run's journal.log).
        Acts like ``with open()`` with a lock so different threads cannot write
        at the same time.
        """
        self.close_file()
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            self._file = open(file_path, "w", encoding="utf-8")
            self.file_path = file_path

    def close_file(self) -> None:
        """
        Stops writing to the journal.log.
        """
        with self._lock:
            if self._file is not None:
                self._file.close()
            self._file = None
            self.file_path = None

    def display_to(
        self, text_box: ScrolledText, show_time: bool, show_level: bool
    ) -> None:
        """
        Display journal lines to ``text_box``. Calling it again replaces the old
        display, which is how changed user preferences are picked up.
        Call from the main thread.
        """
        if self.display is not None:
            self.display.stop()
        self.display = JournalDisplay(text_box, show_time, show_level)

    def _write(self, level: str, lines: list[str], debug_text: str | None) -> None:
        """
        Write handler. This writes lines to each destination from a journal entry.
        ``level``: "ERROR" or "WARNING" is accepted
        ``lines``: list of strings to write
        ``debug_text``: write to the DebugLog as separate debug information.
        """
        entry = JournalEntry(datetime.now(), level, lines)

        # write to the journal.log: always with time and level, so it can be audited.
        with self._lock:
            if self._file is not None:
                self._file.write(format_entry(entry, True, True) + "\n")
                self._file.flush()  # keep the file complete even if the app crashes

        # write to the GUI
        if self.display is not None:
            self.display.add(entry)

        # write to the DebugLog. caller_depth=3 makes the debug log show the line in
        # app code (skipping _write and the journal method called).
        if debug_text is not None:
            if level == "ERROR":
                self._debug.error("[journal] %s", debug_text, caller_depth=3)
            elif level == "WARNING":
                self._debug.warning("[journal] %s", debug_text, caller_depth=3)
            else:
                self._debug.info("[journal] %s", debug_text, caller_depth=3)
