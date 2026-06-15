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
from enum import Enum
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
from src.mtl.process import Process


class MTLProcessorType(int, Enum):
    """
    Enum for the MTL process type selection.
    """

    NONE = 0
    COMPARE = 1
    APPEND = 2


@dataclass(frozen=True)
class MTLRequest:
    """
    Data class that captures a user request for the MTL process.
    """

    process_type: MTLProcessorType
    filter: str
    data_table: str
    mtl_file_path: Path
    input_file_path: Path

    @property
    def report_name(self) -> str:
        return self.filter or "No_Filter"


@dataclass
class MTLUi:
    """
    Data class that captures a processes UI for manipulation.
    """

    progress_bar: tkb.Progressbar
    process_button: tkb.Button
    opt_process: tkb.IntVar
    stext: ScrolledText


class MTLController(ProcessController):
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
        req: MTLRequest,
        ui: MTLUi,
    ) -> None:
        """
        Opens a new thread and starts the subroutine.
        """
        _started = time.perf_counter()
        try:
            process = Process(
                self._controller.report,
                req.filter,
                req.data_table,
                str(req.mtl_file_path),
                str(req.input_file_path),
            )

            if req.process_type == MTLProcessorType.APPEND:
                self._controller.report.info("Appending data...")
                process.append_input()
            else:
                self._controller.report.info("Comparing data...")
                process.compare_input()

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
            self.window.after(
                1, lambda: ui.opt_process.set(MTLProcessorType.NONE.value)
            )
            self.window.after(2, lambda: ui.process_button.config(state=NORMAL))
            completion_time = _ended - _started
            self._controller.report.simple_title(
                f"Processing took: {completion_time:.4f}s"
            )

    def start_process(
        self,
        req: MTLRequest,
        ui: MTLUi,
    ):
        """
        Starts the data processing functions.
        """
        if req.process_type == MTLProcessorType.NONE:
            self.window.after(
                0,
                lambda: self._controller.report.error(
                    "Please select either the Compare or Append radio button.",
                    popup=True,
                ),
            )
            return

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
