# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH
# This tool was created with the help of AI.

# stdlib
from threading import Thread

# third party
import ttkbootstrap as tkb
from ttkbootstrap.widgets.scrolled import ScrolledText

# local
from m_wave.core.context import AppContext
from m_wave.core.reporting.reporter import Reporter


class WavePackController:
    """
    Base class for every WavePack controller.

    The controller OWNS:
        self.reporter   Reporter, all reporting for this WavePack
        self.processor  the WavePack's processor (set by the subclass), which does
                        the actual work and is given the reporter

    and connects them to:
        self.app        the main window
        self.context    app context (user preferences, user ID, version)
    """

    def __init__(self, app: tkb.Window, context: AppContext) -> None:
        self.app = app
        self.context = context
        self.reporter = Reporter(app)
        self.process_thread: Thread | None = None

    @property
    def is_running(self) -> bool:
        """True while the worker thread is processing."""
        return self.process_thread is not None and self.process_thread.is_alive()

    def display_journal_to(self, text_box: ScrolledText) -> None:
        """
        Show the journal in ``text_box`` using the user's display preferences.
        Call from the main thread. Calling it again picks up changed preferences.

        The preferences only change the GUI. journal.log always has time and level.
        """
        prefs = self.context.user_preferences
        self.reporter.display_journal_to(
            text_box,
            show_time=prefs.get("use_timestamps", False),
            show_level=prefs.get("use_msg_types", False),
        )
