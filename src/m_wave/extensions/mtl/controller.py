# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH
# This tool was created with the help of AI.

# stdlib
from threading import Thread

# third-party
import ttkbootstrap as tkb
from ttkbootstrap.constants import DISABLED, NORMAL

# local core
from m_wave.core.context import AppContext
from m_wave.core.gui_dispatcher import UICall
from m_wave.core.utils import load_configs
from m_wave.core.wavepacks.controller import WavePackController

# local wave pack
from m_wave.extensions.mtl.processor import EventMTLDownloaded, MTLProcessor
from m_wave.extensions.mtl.utils.paths import get_mtl_config_path
from m_wave.extensions.mtl.utils.utils import (
    MTLProcessorRequest,
    MTLProcessorType,
    MTLUiPayload,
)


class MTLController(WavePackController):
    """
    Master thread controller of the reporting, processing and configuration parsing.
    """

    def __init__(self, app: tkb.Window, context: AppContext):
        super().__init__(app, context)
        self._ui_payload: MTLUiPayload | None = None
        self._ui_updating = False
        self.processor = MTLProcessor(
            self.reporter, emit_event=self._queue_processor_event
        )
        self.journal = self.reporter.journal
        self.debug = self.reporter.debug
        self.notify = self.reporter.notifier
        self.context: AppContext = context

        try:
            self.configs = load_configs(get_mtl_config_path())
        except Exception as e:
            msg = f"Could not load configurations, check the general log file: {e}"
            self.journal.error(msg)
            self.notify.error(msg)

    def _queue_processor_event(self, event: EventMTLDownloaded) -> None:
        """
        Worker safe, enqueue data for a handler that runs on the main thread.
        """
        self.register_to_ui(
            UICall(
                callback=self._handle_processor_event,
                args=(event,),
            )
        )

    def _handle_processor_event(self, event: EventMTLDownloaded) -> None:
        """
        Main thread handler, translates processor data into widget updates.
        """
        ui = self._ui_payload
        if ui is None:
            return

        if isinstance(event, EventMTLDownloaded):
            ui.mtl_version.set(event.revision)
            ui.mtl_path.set(str(event.path))

    def _update_progress_ui(
        self, ui: MTLUiPayload, state=DISABLED, start: bool = True
    ) -> None:
        ui.process_button.config(state=state)
        if start:
            ui.progress_bar.start()
        else:
            ui.progress_bar.stop()

    def _finish_process_ui(self) -> None:
        """
        Main thread handler for restoring controls after a worker runs.
        """
        ui = self._ui_payload
        if ui is not None:
            self._update_progress_ui(ui, state=NORMAL, start=False)

        self._ui_payload = None
        self._ui_updating = False

    def start_process(self, request: MTLProcessorRequest, ui: MTLUiPayload) -> None:
        """
        Called on the main thread when the user clicks the process button.
        """
        if self._ui_updating or self.is_running:
            self.notify.warning("Process already running!")
            return

        self.display_journal_to(ui.text_box)

        if request.process_type == MTLProcessorType.APPEND:
            self.notify.info("This process is currently disabled.")
            return

        self._ui_payload = ui
        self._ui_updating = True
        self._update_progress_ui(ui)

        self.process_thread = Thread(
            target=self._worker_thread,
            args=(request,),
            name="MTLProcessor",
            daemon=True,
        )
        try:
            self.process_thread.start()
        except Exception:
            # Thread creation failed
            self._update_progress_ui(ui, state=NORMAL, start=False)
            self._ui_payload = None
            self._ui_updating = False
            raise

    def _worker_thread(self, request: MTLProcessorRequest) -> None:
        """
        Worker thread for one completed process run.
            start_process -> processor.run -> report.finish (or report.finish_with_error)
        """
        reporter = self.reporter
        try:
            report_name = str(
                request.report_name
                if request.report_name is not None
                else "Unfiltered Report"
            )
            report = reporter.start_report(report_name)
            if request.process_type == MTLProcessorType.DOWNLOAD:
                pdf_template = self.processor.download_mtl(request)
                reporter.finish_report(pdf_template)
                reporter.notifier.info(
                    f"Process finished: {pdf_template.status.label}\n"
                    f"Results saved to: {report.folder.name}"
                )
            elif request.process_type == MTLProcessorType.COMPARE:
                pdf_template = self.processor.run_comparison(request)
                reporter.finish_report(pdf_template)
                reporter.notifier.info(
                    f"Process finished: {pdf_template.status.label}\n"
                    f"Results saved to : {report.folder.name}"
                )
            else:
                self.notify.info(
                    "How... did you get here? No processor type was found, but the app attempted to process something."
                )

        except Exception as error:
            reporter.finish_report_with_error(error)
            self.notify.error(
                f"The process stopped with an unexpected error:\n{error}\n\n"
                "See journal.log in the report folder for more details."
            )
        finally:
            self.register_to_ui(UICall(self._finish_process_ui))
