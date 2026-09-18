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
from m_wave.core.reporting import Reporting


class WavePackController:
    """
    Class helper for type assignment.
    """

    def __init__(self, app: tkb.Window, context: AppContext) -> None:
        self.app = app
        self.context = context
        self.process_thread: Thread | None = None
        self.report: Reporting | None = None

    def set_report(
        self,
        output_dir: Path,
        user_prefs: dict,
        verbose: bool = False,
    ) -> Reporting:
        """
        Instantiates the main reporting class for the current process run.
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
        Sets/creates a new report by re instantiating. Does not create it automatically.
        Call report.create_report() after.
        """
        if self.report is not None:
            if self.process_thread and self.process_thread.is_alive():
                self.report.error(
                    "Cannot update reporting settings while a process is running",
                    popup=True,
                )
                return

            self.report = self.set_report(
                self.report.output_dir,
                self.context.user_preferences,
            )
            self.report.attach_text_display(text_display)

        else:
            raise RuntimeError("Report not initialized. Cannot reset it.")
