# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH
# This tool was created with the help of AI.

"""
User-facing pop-ups and questions. This is the only reporting module that knows
about Tk dialogs.

    notifier = Notifier(app)
    notifier.info("Processing finished.")
    if notifier.ask("Overwrite the MTL file?", run_log=session.log):
        ...

Pop-ups are queued and shown one at a time (FIFO) on the Tk main thread, so any
method is safe to call from a worker thread.

A Notifier does NOT write to the run log by itself. If a message matters to the
technical reviewer, log it with RunLog as well. ``ask()`` is the exception: pass
``run_log`` and the question and answer are both recorded.
"""

from __future__ import annotations

# stdlib
import logging
import threading
from collections.abc import Callable
from queue import SimpleQueue
from typing import TYPE_CHECKING, Any

# third party
from ttkbootstrap.dialogs import Messagebox

if TYPE_CHECKING:
    import ttkbootstrap as tkb

    from m_wave.core.reporting.run_log import RunLog

logger = logging.getLogger(__name__)

ModalFunc = Callable[..., Any]


class Notifier:
    """Queues ttkbootstrap message boxes onto the Tk main thread."""

    def __init__(self, parent_window: tkb.Window | None) -> None:
        self.parent_window = parent_window
        self._queue: SimpleQueue[tuple[ModalFunc, str, str, Callable | None]] = (
            SimpleQueue()
        )
        self._busy = False
        self._lock = threading.Lock()

    # -- queue --------------------------------------------------------------
    def _enqueue(
        self, func: ModalFunc, msg: str, title: str, on_result: Callable | None = None
    ) -> None:
        if self.parent_window is None:
            logger.warning("No window for pop-up '%s': %s", title, msg)
            if on_result is not None:
                on_result(None)
            return
        self._queue.put((func, msg, title, on_result))
        with self._lock:
            if self._busy:
                return
            self._busy = True
        self.parent_window.after(0, self._show_next)

    def _show_next(self) -> None:
        """Runs on the Tk thread. Shows one modal, then schedules the next."""
        if self._queue.empty():
            with self._lock:
                self._busy = False
            return
        func, msg, title, on_result = self._queue.get()
        result = None
        try:
            result = func(msg, title=title, parent=self.parent_window)
        except Exception:
            logger.exception("Pop-up failed: %s", title)
        finally:
            if on_result is not None:
                on_result(result)
            self.parent_window.after(0, self._show_next)  # type: ignore[union-attr]

    # -- messages -----------------------------------------------------------
    def info(self, msg: str, title: str = "You should know...") -> None:
        logger.debug("Pop-up (info): %s", msg)
        self._enqueue(Messagebox.show_info, msg, title)

    def warning(self, msg: str, title: str = "Warning!") -> None:
        logger.debug("Pop-up (warning): %s", msg)
        self._enqueue(Messagebox.show_warning, msg, title)

    def error(self, msg: str, title: str = "An error has occurred!") -> None:
        logger.debug("Pop-up (error): %s", msg)
        self._enqueue(Messagebox.show_error, msg, title)

    def critical(self, msg: str, title: str = "CRITICAL FAILURE") -> None:
        logger.debug("Pop-up (critical): %s", msg)
        self._enqueue(Messagebox.show_error, msg, title)

    # -- questions ----------------------------------------------------------
    def ask(
        self,
        msg: str,
        title: str = "Input needed",
        yes_text: str = "Yes",
        no_text: str = "No",
        default: bool = False,
        run_log: RunLog | None = None,
    ) -> bool:
        """
        Ask a yes/no question and wait for the answer.

        From a worker thread: the dialog is queued on the Tk thread and this call
        blocks until answered. From the Tk main thread: the dialog is shown
        directly (blocking the main thread waiting on itself would deadlock).

        Returns True for ``yes_text``. Without a window, returns ``default``.
        Pass ``run_log`` to record the question and answer for reviewers.
        """
        if run_log is not None:
            run_log.question(f"{msg}  [{yes_text} / {no_text}]", stacklevel=2)

        def _question(message: str, title: str, parent: Any) -> Any:
            return Messagebox.show_question(
                message,
                title=title,
                parent=parent,
                buttons=[f"{no_text}:secondary", f"{yes_text}:primary"],
            )

        if self.parent_window is None:
            choice = yes_text if default else no_text
            logger.warning("No window to ask '%s'. Assuming '%s'.", msg, choice)
        elif threading.current_thread() is threading.main_thread():
            choice = _question(msg, title, self.parent_window)
        else:
            answered = threading.Event()
            holder: dict[str, Any] = {}

            def _on_result(result: Any) -> None:
                holder["value"] = result
                answered.set()

            self._enqueue(_question, msg, title, on_result=_on_result)
            answered.wait()
            choice = holder.get("value")

        answer = str(choice).strip().lower() == yes_text.strip().lower()
        if run_log is not None:
            run_log.answer(yes_text if answer else no_text, stacklevel=2)
        logger.debug("Question '%s' answered: %r", msg, choice)
        return answer
