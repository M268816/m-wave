# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH
# This tool was created with the help of AI.

# stdlib
from pathlib import Path
from threading import Thread

# third party
import ttkbootstrap as tkb
from ttkbootstrap.widgets.scrolled import ScrolledText

# local
from m_wave.core.context import AppContext
from m_wave.core.paths import PATHS
from m_wave.core.reporting.notifier import Notifier
from m_wave.core.reporting.reporting import Reporting
from m_wave.core.reporting.run_log import RunLog
from m_wave.core.reporting.run_session import FailureTemplateFactory, RunSession


class WavePackController:
    """
    A WavePack logic controller class. This class is used to control the reporting,
    GUI, and other process control methods for a WavePack.

    Basic structure is defined here for root composition:
    app = root app connection
    context = root context connection

    Reporting tools every controller gets:
    run_log  = RunLog, the technical run log (also mirrored to the GUI)
    notifier = Notifier, pop-ups and questions
    start_session() = a RunSession for one process run (run folder, run.log, PDF)

    The legacy ``set_report`` / ``reset_report`` / ``self.report`` API is kept for
    WavePacks that still use ``Reporting``. New WavePacks should not use it.
    """

    def __init__(self, app: tkb.Window, context: AppContext) -> None:
        self.app = app
        self.context = context
        self.process_thread: Thread | None = None

        # New reporting API
        self.run_log = RunLog()
        self.notifier = Notifier(app)

        # Legacy reporting API (MTL, TDG)
        self.report: Reporting | None = None

    # -------------------------------------------------------------------------
    # New reporting API
    # -------------------------------------------------------------------------
    @property
    def is_running(self) -> bool:
        return self.process_thread is not None and self.process_thread.is_alive()

    def attach_display(self, text_display: ScrolledText) -> None:
        """
        Mirror the run log into ``text_display``. Call from the Tk main thread.
        The user preferences for timestamps/levels only affect this display.
        """
        prefs = self.context.user_preferences
        self.run_log.attach_display(
            text_display,
            show_timestamps=prefs.get("use_timestamps", False),
            show_levels=prefs.get("use_msg_types", False),
        )

    def start_session(
        self,
        name: str,
        output_dir: Path | None = None,
        failure_template: FailureTemplateFactory | None = None,
    ) -> RunSession:
        """
        Create (but do not open) a RunSession for one process run. Use it as a
        context manager inside the worker thread:

            with self.start_session("Example Report") as session:
                ...
        """
        return RunSession(
            output_dir or PATHS.reports_dir,
            name,
            log=self.run_log,
            failure_template=failure_template,
        )

    # -------------------------------------------------------------------------
    # Legacy reporting API
    # -------------------------------------------------------------------------
    def set_report(
        self,
        output_dir: Path,
        user_prefs: dict,
        verbose: bool = False,
    ) -> Reporting:
        """
        Deprecated. Instantiates the legacy Reporting wrapper for a process run.
        """
        return Reporting(
            self.app,
            output_dir,
            verbose_printing=verbose,
            use_timestamps=user_prefs.get("use_timestamps", False),
            use_msg_types=user_prefs.get("use_msg_types", False),  # type: ignore
        )

    def reset_report(
        self,
        text_display: ScrolledText,
    ) -> None:
        """
        Deprecated. Re-instantiates the legacy Reporting wrapper so changed user
        preferences are applied. Call report.create_report() after.
        """
        if self.report is not None:
            if self.is_running:
                self.notifier.error(
                    "Cannot update reporting settings while a process is running"
                )
                return

            self.report = self.set_report(
                self.report.output_dir,
                self.context.user_preferences,
            )
            self.report.attach_text_display(text_display)

        else:
            raise RuntimeError("Report not initialized. Cannot reset it.")
