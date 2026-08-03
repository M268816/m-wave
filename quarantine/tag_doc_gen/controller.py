# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
#
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.app.gui import AppWindow
    from src.app.controller import AppController

# stdio
import time
from threading import Thread

# third-party
from ttkbootstrap.constants import DISABLED, NORMAL

# local
from src.app.utils import ProcessController
from src.tag_doc_gen.process import Process

from src.tag_doc_gen.utils import (
    TagDocGenRequest,
    TagDocGenUi,
    TagGeneratorType,
)


class TagDocGenController(ProcessController):
    """
    Master controller of the MES process.
    """

    def __init__(self, window: AppWindow):
        super().__init__()
        self.window = window
        self._controller: AppController = window.controller

    @property
    def report(self):
        return self._controller.report

    def _start_thread(
        self,
        req: TagDocGenRequest,
        ui: TagDocGenUi,
    ) -> None:
        """
        Opens a new thread and starts the subroutine.
        """
        _started = time.perf_counter()
        try:
            process = Process(self.report, req)
            process.run(req.processor_type, req.file_type)
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
                1, lambda: ui.gen_opt_cbox.set(TagGeneratorType.NONE.value)
            )
            self.window.after(2, lambda: ui.process_button.config(state=NORMAL))
            completion_time = _ended - _started
            self._controller.report.simple_title(
                f"Processing took: {completion_time:.4f}s"
            )

    def start_process(
        self,
        req: TagDocGenRequest,
        ui: TagDocGenUi,
    ):
        """
        Starts the data processing functions.
        """
        if req.processor_type == TagGeneratorType.NONE.value:
            self.window.after(
                0,
                lambda: self._controller.report.error(
                    "Please select a document to generate.",
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
        self._controller.reset_report(
            ui.scrolled_text,
            f"{req.kepware_channel.get()}_{req.kepware_device.get()}_{req.report_name}",
        )

        ui.progress_bar.start()

        self.process_thread = Thread(
            target=lambda: self._start_thread(req, ui),
            daemon=True,
        )
        self.process_thread.start()
