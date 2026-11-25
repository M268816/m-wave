# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH
# This tool was created with the help of AI.


# stdlib
from __future__ import annotations

import logging
import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass, field
from queue import Empty, SimpleQueue
from threading import Lock
from typing import Any


@dataclass
class UICall:
    callback: Callable
    args: tuple[Any, ...] = field(default_factory=tuple)
    kwargs: dict[str, Any] = field(default_factory=dict)


class GUIUpdateDispatcher:
    """
    Tk widgets are queued from background worker threads created by the wavepack
    and written to the main thread through this dispatcher.

    From the main GUI thread, this checks every XX ms with after() and updates any
    widgets in the queue.
    """

    MAX_CALLS_PER_TICK = 100

    def __init__(self, root: tk.Misc, interval_ms: int = 250) -> None:
        if interval_ms < 1:
            raise ValueError("interval_ms must be at least 1")

        self._root = root
        self._interval_ms = interval_ms
        self._events: SimpleQueue[UICall] = SimpleQueue()
        self._lock = Lock()
        self._closed = False
        self._id: str | None = root.after(
            self._interval_ms,
            self._drain,
        )

    def register(self, call: UICall) -> bool:
        """
        Queue a callback for the main thread.

        This method does not call Tkinter, so a worker can call it safely.
        Returns False if the dispatcher is closed.
        """
        with self._lock:
            if self._closed:
                return False

            self._events.put(call)
            return True

    def close(self) -> None:
        """
        Stop future qeueue checks. Call this form the main thread.
        """
        with self._lock:
            if self._closed:
                return

            self._closed = True
            id = self._id
            self._id = None

        if id is not None:
            try:
                self._root.after_cancel(id)
            except tk.TclError:
                pass

    def _drain(self) -> None:
        """
        Drains the event queue.
        Attempts to execute the ui call.
        Runs only on the main thread.
        """
        with self._lock:
            if self._closed:
                return
            self._id = None

        for _ in range(self.MAX_CALLS_PER_TICK):
            try:
                call = self._events.get_nowait()
            except Empty:
                break

            try:
                call.callback(*call.args, **call.kwargs)
            except Exception:
                logging.getLogger(__name__).exception("A queued GUI update failed.")

        with self._lock:
            if self._closed:
                return

        try:
            self._id = self._root.after(
                self._interval_ms,
                self._drain,
            )
        except tk.TclError:
            self.close()
