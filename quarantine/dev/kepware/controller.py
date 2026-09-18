# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
#
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH

# Futures for type annotations
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.app.gui import AppWindow

# stdio
import time
from dataclasses import dataclass
from pathlib import Path
from threading import Thread

# third-party
import ttkbootstrap as tkb
from ttkbootstrap.constants import NORMAL, DISABLED
from ttkbootstrap.widgets.scrolled import ScrolledText

# local
from src.app.controller import (
    AppController,
)
from src.app.utils import ProcessController
from src.kepware.process import Process


@dataclass(frozen=True)
class KepwareRequest:
    """
    Data class that captures a user request for the MTL process.
    """

    report_name: str
    file_path_1: Path
    file_path_2: Path


@dataclass
class KepwareUi:
    """
    Data class that captures a processes UI for manipulation.
    """

    progress_bar: tkb.Progressbar
    process_button: tkb.Button
    stext: ScrolledText


class KepwareController(ProcessController):
    """
    Master controller of the reporting, processing and configuration parsing.

    Attributes
    ----------
    window: tkb.Window
        a root window used to display the application

    Methods
    -------
    start_process(ProcessRequest, ProcessUI)
        Starts the data processing functions.
    """

    def __init__(self, window: AppWindow):
        super().__init__()
        self.window = window
        self._controller: AppController = window.controller

    def _start_thread(
        self,
        request: KepwareRequest,
        ui: KepwareUi,
    ) -> None:
        """
        Opens a new thread and starts the subroutine.
        """
        _started = time.perf_counter()
        try:
            process = Process(
                self._controller.report,
                request.file_path_1,
                request.file_path_2,
            )

            process.run()

        except Exception as e:
            self._controller.report.exception(
                f"Subroutine process error:\n{e}",
                popup=True,
            )
        finally:
            _ended = time.perf_counter()
            self.window.after(
                0,
                lambda: self._controller.report.info(
                    "Subroutine ended.",
                    popup=True,
                ),
            )
            self.window.after(0, lambda: ui.progress_bar.stop())
            self.window.after(2, lambda: ui.process_button.config(state=NORMAL))
            completion_time = _ended - _started
            self._controller.report.simple_title(
                f"Processing took: {completion_time:.4f}s"
            )

    def start_process(
        self,
        req: KepwareRequest,
        ui: KepwareUi,
    ):
        """
        Starts the data processing functions.
        """

        if self.process_thread and self.process_thread.is_alive():
            self.window.after(
                0,
                lambda: self._controller.report.warning(
                    "Process already running!",
                    popup=True,
                ),
            )
            return

        ui.process_button.config(state=DISABLED)
        self._controller.reset_report(ui.stext, req.report_name)

        ui.progress_bar.start()

        self.process_thread = Thread(
            target=lambda: self._start_thread(req, ui),
            daemon=True,
        )
        self.process_thread.start()
