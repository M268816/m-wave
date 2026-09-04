# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
#
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from m_wave.core.gui import App
    from m_wave.core.context import AppContext
    from m_wave.core.reporting import Reporting

# stdio
import time
from threading import Thread

# third-party
from ttkbootstrap.constants import DISABLED, NORMAL

# local core
from m_wave.core.wavepack_controller import WavePackController
from m_wave.core.paths import PATHS

# local wave pack
from m_wave.wave_packs.tag_doc_gen.process import Process
from m_wave.wave_packs.tag_doc_gen.utils import (
    ProcessRequest,
    UiContext,
    DocGeneratorType,
)


class Controller(WavePackController):
    """
    Master controller of the MES process.
    """

    def __init__(self, app: App, context: AppContext):
        super().__init__(app, context)
        self.app: App = app
        self.context: AppContext = context

        self.report: Reporting = self.set_report(
            PATHS.reports_dir,
            self.context.user_preferences,
        )

    def _start_thread(
        self,
        req: ProcessRequest,
        ui: UiContext,
    ) -> None:
        """
        Opens a new thread and starts the subroutine.
        """
        _started = time.perf_counter()
        try:
            process = Process(self.report, req)
            process.run(req.processor_type, req.file_type)
        except Exception as e:
            self.report.exception(
                f"Subroutine process error:\n{e}",
                popup=True,
            )
        finally:
            _ended = time.perf_counter()
            self.app.after(
                0,
                lambda: self.report.info(
                    "Subroutine ended.",
                    popup=True,
                ),
            )
            self.app.after(0, lambda: ui.progress_bar.stop())
            self.app.after(1, lambda: ui.gen_opt_cbox.set(DocGeneratorType.NONE.value))
            self.app.after(2, lambda: ui.process_button.config(state=NORMAL))
            completion_time = _ended - _started
            self.report.simple_title(f"Processing took: {completion_time:.4f}s")

    def start_process(
        self,
        req: ProcessRequest,
        ui: UiContext,
    ):
        """
        Starts the data processing functions.
        """
        if self.report is not None:
            self.reset_report(ui.scrolled_text)
            if req.report_name is not None:
                report_name = req.report_name
            else:
                report_name = f"{req.kepware_channel.get()}_{req.kepware_device.get()}"
            self.report.create_report(report_name)
        else:
            raise RuntimeError(
                "Report was never set, cannot start the processing functions."
            )
        if req.processor_type == DocGeneratorType.NONE.value:
            self.app.after(
                0,
                lambda: self.report.error(
                    "Please select a document to generate.",
                    popup=True,
                ),
            )
            return

        if self.process_thread and self.process_thread.is_alive():
            self.app.after(
                0,
                lambda: self.report.warning(
                    "Process already running!",
                    popup=True,
                ),
            )
            return

        ui.process_button.config(state=DISABLED)
        self.report.save_report()

        ui.progress_bar.start()

        self.process_thread = Thread(
            target=lambda: self._start_thread(req, ui),
            daemon=True,
        )
        self.process_thread.start()
