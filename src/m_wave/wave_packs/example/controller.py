# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH
# This tool was created with the help of AI.

# stdlib
import time
from dataclasses import dataclass
from pathlib import Path
from threading import Thread

# third-party
import ttkbootstrap as tkb
from ttkbootstrap.constants import DISABLED, NORMAL
from ttkbootstrap.widgets.scrolled import ScrolledText

# local core
from m_wave.core.context import AppContext
from m_wave.core.paths import PATHS
from m_wave.core.wavepack_controller import WavePackController

# local wave_pack
from m_wave.wave_packs.example.process import ExampleProcess


@dataclass(frozen=True)
class ExampleRequest:
    """
    Data class that captures a user request for the MTL process.
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
        self.report = self.set_report(
            PATHS.reports_dir,
            self.context.user_preferences,
        )

    def _start_thread(
        self,
        request: ExampleRequest,
        ui: ExampleUi,
    ) -> None:
        """
        Opens a new thread and starts the subroutine.
        """
        _started = time.perf_counter()
        if self.report:
            try:
                process = ExampleProcess(
                    self.report,
                    request.file_path,
                )
                process.run()
            except Exception as e:
                self.report.exception(
                    f"Subroutine process error:\n{e}",
                    popup=True,
                )
            finally:
                _ended = time.perf_counter()
                self.app.after(
                    0,
                    lambda r=self.report: r.info(
                        "Subroutine ended.",
                        popup=True,
                    ),
                )
                self.app.after(0, lambda: ui.progress_bar.stop())
                self.app.after(2, lambda: ui.process_button.config(state=NORMAL))
                completion_time = _ended - _started
                self.report.simple_title(f"Processing took: {completion_time:.4f}s")
        else:
            raise RuntimeError("Cannot start process. Report not initialized.")

    def start_process(
        self,
        req: ExampleRequest,
        ui: ExampleUi,
    ):
        """
        Starts the data processing functions.
        """
        # Make sure that the report object was initialized.
        if self.report:
            # Create a new report folder, and attach any ui elements
            self.reset_report(ui.stext)
            self.report.create_report("Example Report")

            # Make sure that there is not already process thread running.
            if self.process_thread and self.process_thread.is_alive():
                self.app.after(
                    0,
                    lambda r=self.report: r.warning(
                        "Process already running!",
                        popup=True,
                    ),
                )
                return

            # Update any UI items for the process.
            ui.process_button.config(state=DISABLED)
            ui.progress_bar.start()

            # Start a new process thread.
            self.process_thread = Thread(
                target=lambda: self._start_thread(req, ui),
                daemon=True,
            )
            self.process_thread.start()
        else:
            raise RuntimeError("Cannot start process. Reprot not initalzied.")
