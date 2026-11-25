# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH
# This tool was created with the help of AI.

"""
Example WavePack processor: the reference pattern for using the Reporter.

    reporter.journal    what a technical reviewer needs to follow the run
    reporter.artifacts  files a technical reviewer can open (before/after, CSVs)
    reporter.debug      detail only you need when debugging
    reporter.notifier   pop-ups / questions for the person at the screen
    (return value)      the PDF template: the summary for non-technical reviewers

The processor never imports tkinter or ttkbootstrap. Everything the user sees
goes through reporter.notifier, so the processor can be tested without a GUI.
"""

# stdlib

# local
from m_wave.core.gui_events import UIEventSink, ignore_ui_event
from m_wave.core.reporting.reporter import Reporter


class WavePackProcessor:
    def __init__(
        self,
        reporter: Reporter,
        ui_event_sink: UIEventSink | None = None,
    ) -> None:
        self._emit_ui_event = ui_event_sink or ignore_ui_event

        self.reporter = reporter
        self.journal = reporter.journal
        self.debug = reporter.debug
        self.notify = reporter.notifier

    def ui_emitter(self) -> None:
        """
        Send a status string change event to the GUI.
        Update this with your own events and emitter.

        self._emit_ui_event(Event())
        """
