# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH
# This tool was created with the help of AI.

# stdlib
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from threading import Thread

# third-party
import ttkbootstrap as tkb
from ttkbootstrap.constants import DISABLED, NORMAL
from ttkbootstrap.widgets.scrolled import ScrolledText

# local
from m_wave.content.example.pdf_template import ExamplePDFReportTemplate
from m_wave.content.example.process import ExampleProcess
from m_wave.core.context import AppContext
from m_wave.core.reporting.pdf_utils import PDFReportStatus
from m_wave.core.reporting.run_session import RunSession
from m_wave.core.wavepacks.controller import WavePackController

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExampleRequest:
    """
    Data class that captures a user request for the Example process.
    """

    report_name: str
    file_path: Path


@dataclass
class ExampleUi:
    """
    Data class that captures a processes UI for manipulation.
    """

    progress_bar: tkb.Progressbar
    process_button: tkb.Button
    stext: ScrolledText


def _failure_template(
    session: RunSession, error: BaseException
) -> ExamplePDFReportTemplate:
    """ERRORED PDF used by the session when the process raises before its own PDF."""
    return ExamplePDFReportTemplate(
        title="Example Report",
        report_id=session.report_id,
        user=session.user,
        created_date=session.started_at,
        status=PDFReportStatus.ERRORED,
        subtitle="The process stopped before it finished.",
        example_str=f"{type(error).__name__}: {error}",
    )


class ExampleController(WavePackController):
    """
    Master controller of the reporting, processing and app context value handling.
    """

    def __init__(self, app: tkb.Window, context: AppContext):
        super().__init__(app, context)
        # self.app can be the generic Window object here because we just need to check the
        # .after() method with it. Otherwise, change this to import App with the
        # TYPE_CHECKING import blocker
        self.app = app
        self.context: AppContext = context

    def _run_in_thread(
        self,
        request: ExampleRequest,
        ui: ExampleUi,
    ) -> None:
        """
        Worker thread body. Owns one RunSession from start to finish.
        """
        started = time.perf_counter()
        try:
            with self.start_session(
                request.report_name, failure_template=_failure_template
            ) as session:
                process = ExampleProcess(session, self.notifier, request.file_path)
                status = process.run()
            self.notifier.info(
                f"Process finished: {status.label}\n\n"
                f"Results are in:\n{session.run_dir}"
            )
        except Exception as error:
            # Already in run.log and the developer log (via the session).
            self.notifier.error(
                f"The process stopped with an error:\n{error}\n\n"
                "See run.log in the report folder for details."
            )
        finally:
            logger.debug("Example process took %.4fs", time.perf_counter() - started)
            self.app.after(0, ui.progress_bar.stop)
            self.app.after(2, lambda: ui.process_button.config(state=NORMAL))

    def start_process(
        self,
        req: ExampleRequest,
        ui: ExampleUi,
    ) -> None:
        """
        Starts the data processing functions. Called on the Tk main thread.
        """
        if self.is_running:
            self.notifier.warning("Process already running!")
            return

        # Re-attach so changed display preferences take effect for this run.
        self.attach_display(ui.stext)

        ui.process_button.config(state=DISABLED)
        ui.progress_bar.start()

        self.process_thread = Thread(
            target=lambda: self._run_in_thread(req, ui),
            name="ExampleProcess",
            daemon=True,
        )
        self.process_thread.start()
