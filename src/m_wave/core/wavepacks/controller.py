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
from m_wave.core.gui_dispatcher import GUIUpdateDispatcher, UICall
from m_wave.core.gui_events import UIEvent
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

        dispatcher = getattr(app, "ui_dispatcher", None)
        if not isinstance(dispatcher, GUIUpdateDispatcher):
            raise RuntimeError("The applicaiton must provide a GUIUpdateDispatcher.")
        self.ui_dispatcher = dispatcher
        self.ui_updating: bool = False

        self.reporter = Reporter(app)
        self.process_thread: Thread | None = None

    @property
    def is_running(self) -> bool:
        """True while the worker thread is processing."""
        return self.process_thread is not None and self.process_thread.is_alive()

    @property
    def has_event_handler(self) -> bool:
        """
        Returns True if this frame has properly set up the ui event handler.
        """
        return type(self).handle_ui_event is not WavePackController.handle_ui_event

    def handle_ui_event(self, event: UIEvent) -> None:
        """
        Main thread processor ui event handler, each event type must be added
        here.
        """

    def register_to_ui(
        self,
        uicall: UICall,
    ) -> bool:
        """
        Queue a GUI callback to run on tk's main thread.
        """
        return self.ui_dispatcher.register(uicall)

    def queue_ui_event(self, event: UIEvent) -> None:
        """
        Worker save ui event queue helper. Queues the event handler from the main thread.
        """
        if self.has_event_handler:
            self.register_to_ui(
                UICall(
                    callback=self.handle_ui_event,
                    args=(event,),
                )
            )
        else:
            raise NotImplementedError(
                "Subclasses must overwrite handle_ui_event for each ui event case."
            )

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
