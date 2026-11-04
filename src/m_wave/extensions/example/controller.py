# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH
# This tool was created with the help of AI.

# stdlib
from dataclasses import dataclass
from threading import Thread

# third-party
import ttkbootstrap as tkb
from ttkbootstrap.constants import DISABLED, NORMAL
from ttkbootstrap.widgets.scrolled import ScrolledText

# local
from m_wave.core.context import AppContext
from m_wave.core.wavepacks.controller import WavePackController
from m_wave.extensions.example.processor import Processor, ProcessorRequest

__all__ = ["ExampleController", "ExampleUiPayload", "ProcessorRequest"]


@dataclass
class ExampleUiPayload:
    """
    The widgets the controller updates while a report is running.
    """

    progress_bar: tkb.Progressbar
    process_button: tkb.Button
    stext: ScrolledText


class ExampleController(WavePackController):
    """
    Owns the Reporter (from WavePackController) and the ExampleProcessor, and
    runs the processor in a worker thread so the window stays responsive.
    """

    def __init__(self, app: tkb.Window, context: AppContext):
        super().__init__(app, context)
        self.processor = Processor(self.reporter)

    def start_process(self, request: ProcessorRequest, ui: ExampleUiPayload) -> None:
        """Called on the main thread when the user clicks the process button."""
        if self.is_running:
            self.reporter.notifier.warning("Process already running!")
            return

        # Re-attach so changed display preferences take effect for this run.
        self.display_journal_to(ui.stext)

        ui.process_button.config(state=DISABLED)
        ui.progress_bar.start()

        self.process_thread = Thread(
            target=self._run_in_thread,
            args=(request, ui),
            name="ExampleProcess",
            daemon=True,
        )
        self.process_thread.start()

    def _run_in_thread(self, request: ProcessorRequest, ui: ExampleUiPayload) -> None:
        """
        Worker thread. One complete run:
            start_run -> processor.run -> finish_run (or finish_run_with_error)
        """
        reporter = self.reporter
        try:
            report = reporter.start_report(request.report_name)
            template = self.processor.run(request)
            reporter.finish_report(template)
            reporter.notifier.info(
                f"Process finished: {template.status.label}\n\n"
                f"Results are in:\n{report.folder}"
            )

        except Exception as error:
            reporter.finish_report_with_error(error)
            reporter.notifier.error(
                f"The process stopped with an error:\n{error}\n\n"
                "See journal.log in the report folder for details."
            )

        finally:
            # Widgets may only be changed on the main thread, so use after().
            self.app.after(0, ui.progress_bar.stop)
            self.app.after(0, lambda: ui.process_button.config(state=NORMAL))
