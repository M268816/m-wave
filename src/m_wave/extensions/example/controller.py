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
from m_wave.core.gui_dispatcher import UICall
from m_wave.core.gui_events import UIEvent
from m_wave.core.wavepacks.controller import WavePackController
from m_wave.extensions.example.gui_events import (
    EventExample,
    EventExampleTwo,
)
from m_wave.extensions.example.processor import (
    Processor,
    ProcessorRequest,
)


@dataclass
class UIRefs:
    """
    The widgets the controller updates while a report is running.
    """

    progress_bar: tkb.Progressbar
    process_button: tkb.Button
    stext: ScrolledText
    status_var: tkb.StringVar


class ExampleController(WavePackController):
    """
    Owns the Reporter (from WavePackController) and the ExampleProcessor, and
    runs the processor in a worker thread so the window stays responsive.
    """

    def __init__(self, app: tkb.Window, context: AppContext):
        super().__init__(app, context)
        self.processor = Processor(self.reporter, event_sink=self.queue_ui_event)

    def handle_ui_event(self, event: UIEvent) -> None:
        """
        Main thread processor ui event handler.
        Each event type must be added to catch it here.
        """
        ui = self.ui_payload
        if ui is None:
            return

        if isinstance(event, EventExample):
            ui.status_var.set(event.message)

        if isinstance(event, EventExampleTwo):
            ui.progress_bar.config(value=event.progress)
            ui.process_button.config(state=event.button_state)

    def _finish_process_ui(self) -> None:
        """
        Restores the controls after the process has finished, pushed from worker
        to main thread.
        """
        ui = self.ui_payload
        if ui is not None:
            self._update_progress_ui(ui, state=NORMAL, start=False)
            ui.status_var.set("Run Finished.")

        self.ui_payload = None
        self.ui_updating = False

    def _update_progress_ui(
        self, ui: UIRefs, state=DISABLED, start: bool = True
    ) -> None:
        """
        Update the process button and progress bar.
        ``state``: use DISABLED or NORMAL
        ``start``: Boolean (Default: True)
        """
        ui.process_button.config(state=state)
        if start:
            ui.progress_bar.start()
        else:
            ui.progress_bar.stop()

    def start_process(self, request: ProcessorRequest, ui: UIRefs) -> None:
        """Called on the main thread when the user clicks the process button."""
        if self.is_running or self.ui_updating:
            self.reporter.notifier.warning("Process already running!")
            return

        # Re-attach so changed display preferences take effect for this run.
        self.display_journal_to(ui.stext)

        # Updating the UI on the main thread is fine here,
        # but make sure to update UI objects with a UICall while in a thread.
        # See _run_in_thread below.
        self.ui_payload = ui
        self.ui_updating = True
        ui.status_var.set("Starting...")
        self._update_progress_ui(ui)

        self.process_thread = Thread(
            target=self._run_in_thread,
            args=(request,),
            name="ExampleProcess",
            daemon=True,
        )

        try:
            self.process_thread.start()
        except Exception:
            self._update_progress_ui(ui, state=NORMAL, start=False)
            self.ui_payload = None
            self.ui_updating = False
            raise

    def _run_in_thread(self, request: ProcessorRequest) -> None:
        """
        Worker thread. One complete run:
            start_run -> processor.run -> finish_run (or finish_run_with_error)

        Reminder: UI updates are dispatched with self.register_to_ui through a method
        call, using the UICall dataclass.
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
            msg = (
                "The process stopped with an error:\n"
                "See journal.log in the report folder for details.\n\n"
            )
            reporter.finish_report_with_error(error)
            reporter.notifier.error(msg + f": {error}")
            reporter.debug.error(msg + ": %s", error, error=error)

        finally:
            # Widgets/UI may only be changed on the main thread, so use register_to_ui
            # when IU changes occur within a thread.
            # This example stops the progress bar while still in the worker thread by
            # queueing it to the main thread instead.
            self.register_to_ui(UICall(callback=self._finish_process_ui))
