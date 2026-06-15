# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
#
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH

from __future__ import annotations
from typing import TYPE_CHECKING

from ttkbootstrap.dialogs import Messagebox

if TYPE_CHECKING:
    from src.app.gui import AppWindow
    from src.app.controller import AppController

# stdio
import time
from dataclasses import dataclass
from enum import Enum
from threading import Thread

# third-party
import ttkbootstrap as tkb
from ttkbootstrap.constants import DISABLED

# local
from src.app.utils import ProcessController
from src.tag_formatter.process import TagFormatterProcess


class TagProcessorType(int, Enum):
    NONE = 0
    TAG_TO_ATTRIBUTE = 1
    KEPWARE_TO_FILTER = 2


@dataclass
class TagFormatterRequest:
    """
    Data class that captures a processes data for manipulation.
    """

    equipment_code: tkb.StringVar
    kepware_channel: tkb.StringVar
    kepware_device: tkb.StringVar
    department_code: tkb.StringVar
    tag_prefix_length: tkb.StringVar
    node_id_prefix: tkb.StringVar
    namespace_index: tkb.StringVar
    processor_type: TagProcessorType


@dataclass
class TagFormatterUi:
    """
    Data class that captures a processes UI widgets for manipulation.
    """

    equipment_code: tkb.Entry
    kepware_channel: tkb.Entry
    kepware_device: tkb.Entry
    department_code: tkb.Entry
    tag_prefix_length: tkb.Spinbox
    node_id_prefix: tkb.Entry
    namespace_index: tkb.Spinbox
    progress_bar: tkb.Progressbar
    start_button: tkb.Button


class TagFormatterController(ProcessController):
    """
    Master controller of the MES process.
    """

    def __init__(self, window: AppWindow):
        super().__init__()
        self.window = window
        self._controller: AppController = window.controller

    def _start_thread(
        self,
        req: TagFormatterRequest,
        ui: TagFormatterUi,
    ) -> None:
        """
        Opens a new thread and starts the subroutine.
        """
        _started = time.perf_counter()
        try:
            process = TagFormatterProcess(self._controller.report, req, ui)

            if req.processor_type == TagProcessorType.KEPWARE_TO_FILTER:
                self._controller.report.info("Appending data...")
                process.run()
            else:
                Messagebox.ok(
                    title="Testing",
                    message="This is just a test, no processor type caught selected.",
                )

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
            self.window.after(1, lambda: ui.opt_process.set(ProcessType.NONE.value))
            self.window.after(2, lambda: ui.process_button.config(state=NORMAL))
            completion_time = _ended - _started
            self._controller.report.simple_title(
                f"Processing took: {completion_time:.4f}s"
            )

    def start_process(
        self,
        req: TagFormatterRequest,
        ui: TagFormatterUi,
    ):
        """
        Starts the data processing functions.
        """
        if req.process_type == TagProcessorType.NONE:
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
