# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH
# This tool was created with the help of AI.

"""
Notifier: pop-ups and yes/no questions for the user of the app.
This is the only reporting file that knows about Tk dialogs.

    notifier.info("Processing finished.")
    notifier.warning("The file has hidden sheets.")
    if notifier.ask("Headers differ. Continue anyway?"):
        ...

Safe to call from the worker thread
-----------------------------------
Tk dialogs must be opened on the main thread. When the worker thread calls a
Notifier method, the pop-up is put in a waiting line (a queue) and the main
thread opens it. Pop-ups are shown one at a time, in the order they were asked
for, so they never stack on top of each other.

``ask()`` from the worker thread waits until the user has clicked a button.

What gets recorded
------------------
    * Every pop-up and question  -> DebugLog
    * Every question and answer  -> Journal (reviewers can see what was decided)
    * Plain pop-ups are NOT copied to the Journal. If a message matters to the
      reviewer, also write it with ``journal.info/warning/error``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import ttkbootstrap as tkb

    from m_wave.core.reporting.journal import Journal


# stdlib
import threading
from collections.abc import Callable
from queue import SimpleQueue
from typing import Any

# third party
from ttkbootstrap.dialogs import Messagebox

# local
from m_wave.core.reporting.debug_log import DebugLog


class Notifier:
    def __init__(self, window: tkb.Window | None, journal: Journal) -> None:
        self.window = window
        self.journal = journal
        self._debug = DebugLog()

        # Pop-ups wait queue: (dialog function, message, title, callback)
        self._waiting: SimpleQueue[tuple[Callable, str, str, Callable | None]] = (
            SimpleQueue()
        )
        self._showing = False
        self._lock = threading.Lock()

    def info(self, msg: str, title: str = "You should know...") -> None:
        """
        Show an informational modal.
        """
        self._debug.info("Pop-up (info): %s", msg, caller_depth=2)
        self._queue(Messagebox.show_info, msg, title)

    def warning(self, msg: str, title: str = "Warning!") -> None:
        """
        Show a warning modal.
        """
        self._debug.warning("Pop-up (warning): %s", msg, caller_depth=2)
        self._queue(Messagebox.show_warning, msg, title)

    def error(self, msg: str, title: str = "An error has occurred!") -> None:
        """
        Show an error modal.
        """
        self._debug.error("Pop-up (error): %s", msg, caller_depth=2)
        self._queue(Messagebox.show_error, msg, title)

    def ask(
        self,
        msg: str,
        title: str = "Input needed",
        yes_text: str = "Yes",
        no_text: str = "No",
        default: bool = False,
    ) -> bool:
        """
        Ask a yes/no question and wait for the answer.

        Returns True if the user clicked ``yes_text``. If there is no window
        (for example in a test), returns ``default`` without asking.
        The question and the answer are written to the Journal.
        """
        self.journal.question(f"{msg}  [{yes_text} / {no_text}]")

        def show_question(message: str, title: str, parent: Any) -> Any:
            return Messagebox.show_question(
                message,
                title=title,
                parent=parent,
                buttons=[f"{no_text}:secondary", f"{yes_text}:primary"],
            )

        if self.window is None:
            clicked = yes_text if default else no_text
            self._debug.warning("No window to ask '%s'. Using '%s'.", msg, clicked)

        elif threading.current_thread() is threading.main_thread():
            # Already on the main thread: just show it.
            clicked = show_question(msg, title, self.window)

        else:
            # Worker thread: hand the question to the main thread and wait.
            answered = threading.Event()
            result: dict[str, Any] = {}

            def on_answer(value: Any) -> None:
                result["clicked"] = value
                answered.set()

            self._queue(show_question, msg, title, on_answer)
            answered.wait()
            clicked = result.get("clicked")

        said_yes = str(clicked).strip().lower() == yes_text.strip().lower()
        self.journal.answer(yes_text if said_yes else no_text)
        return said_yes

    def _queue(
        self,
        dialog: Callable,
        msg: str,
        title: str,
        on_close: Callable[[Any], None] | None = None,
    ) -> None:
        """Add a pop-up to the wait queue. Safe from any thread."""
        if self.window is None:
            if on_close is not None:
                on_close(None)
            return

        self._waiting.put((dialog, msg, title, on_close))

        with self._lock:
            if self._showing:
                return  # the main thread is already working through the line
            self._showing = True
        self.window.after(0, self._show_next)

    def _show_next(self) -> None:
        """Runs on the main thread. Shows one pop-up, then moves to the next."""
        if self._waiting.empty():
            with self._lock:
                self._showing = False
            return

        dialog, msg, title, on_close = self._waiting.get()
        clicked = None
        try:
            clicked = dialog(msg, title=title, parent=self.window)
        except Exception as error:
            self._debug.error("Pop-up 's%' could not be shown", title, error=error)
        finally:
            if on_close is not None:
                on_close(clicked)
            self.window.after(0, self._show_next)  # type: ignore[union-attr]
