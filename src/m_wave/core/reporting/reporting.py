# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH
# This tool was created with the help of AI.

"""
LEGACY COMPATIBILITY WRAPPER. Do not use in new code.

``Reporting`` used to do logging, the text report, the GUI display, pop-ups and the
PDF all in one class. Those jobs now live in:

    log_setup.py    developer log (configured once at startup)
    run_log.py      RunLog: technical run log -> run.log + GUI display
    notifier.py     Notifier: pop-ups and ask()
    run_session.py  RunSession: run folder, run ID, run.log file, PDF rendering

This class keeps the old API so WavePacks that have not been migrated yet (MTL,
TDG) keep working. Every method just forwards to the new objects.

Flag mapping (old -> new):
    report=True (default)    -> RunLog (run.log + GUI + developer log)
    report=False, log=True   -> developer log only
    popup=True               -> Notifier, in addition to the above
    verbose                  -> ignored; the console handler in log_setup covers it
    save_report()            -> closes run.log (it is already written as it goes)

Migration: see ``m_wave/content/example`` for the target pattern, then delete
this file once no WavePack imports it.
"""

from __future__ import annotations

# stdlib
import logging
from datetime import datetime
from pathlib import Path

# third party
import ttkbootstrap as tkb
from ttkbootstrap.widgets.scrolled import ScrolledText

# local
from m_wave.core.context import USER
from m_wave.core.reporting.notifier import Notifier
from m_wave.core.reporting.pdf_builder import PDFReportTemplate
from m_wave.core.reporting.run_log import DEFAULT_WIDTH, RunLog
from m_wave.core.reporting.run_session import RunSession
from m_wave.core.utils import DATETIME_FORMAT, DATETIME_FORMAT_MERCK

logger = logging.getLogger(__name__)

# Caller -> Reporting.<level> -> Reporting._emit -> RunLog.<level>
_FORWARD = 2


class Reporting:
    """Deprecated. Forwards to RunLog / Notifier / RunSession. See module docstring."""

    def __init__(
        self,
        parent_window: tkb.Window,
        output_dir: Path,
        verbose_printing: bool = True,
        populate_report: bool = True,
        populate_log: bool = True,
        use_timestamps: bool = True,
        use_msg_types: bool = True,
        timestamp: datetime | None = None,
    ) -> None:
        self.parent_window = parent_window
        self.output_dir = output_dir
        self.verbose = verbose_printing
        self.logging = populate_log
        self.report = populate_report
        self.use_timestamps = use_timestamps
        self.use_msg_types = use_msg_types
        self.width = DEFAULT_WIDTH
        self.user = USER

        self.log = RunLog(width=self.width)
        self.notifier = Notifier(parent_window)
        self.session: RunSession | None = None

        self.timestamp = (timestamp or datetime.now()).strftime(DATETIME_FORMAT)
        self.timestamp_merck = datetime.now().strftime(DATETIME_FORMAT_MERCK)

    # -- old path attributes, now read from the session ---------------------
    @property
    def report_name(self) -> str:
        return self.session.name if self.session else ""

    @property
    def cleaned_name(self) -> str:
        return self.session.cleaned_name if self.session else ""

    @property
    def folder_name(self) -> str:
        return self.session.folder_name if self.session else ""

    @property
    def report_dir(self) -> Path:
        return self.session.run_dir if self.session else Path()

    @property
    def report_path(self) -> Path:
        return self.session.log_path if self.session else Path()

    # -- setup ----------------------------------------------------------------
    def attach_text_display(self, text_display: ScrolledText) -> None:
        self.log.attach_display(
            text_display,
            show_timestamps=self.use_timestamps,
            show_levels=self.use_msg_types,
        )

    def create_report(
        self,
        report_name: str = "Not_Named",
        new_timestamp: datetime | None = None,
        update_dirs: bool = True,
    ) -> None:
        if self.session is not None:
            self.session.close()
        self.session = RunSession(
            self.output_dir, report_name, log=self.log, started_at=new_timestamp
        )
        self.timestamp = self.session.timestamp
        if update_dirs:
            self.session.open()

    def save_report(self, popup: bool = False) -> None:
        """run.log is written live; this just closes it."""
        if self.session is None:
            raise RuntimeError("create_report() must be called before save_report().")
        notice = f"{self.report_name} report saved to: ..//{self.report_path.name}"
        if popup:
            self.notifier.info(notice, "Saving...")
        self.session.close()

    def create_pdf_report(
        self,
        report_template: PDFReportTemplate,
        output_dir: Path | None = None,
        page_size: tuple[float, float] | None = None,
        logo_path: Path | None = None,
    ) -> Path | None:
        if self.session is None:
            self.error("create_report() must be called before create_pdf_report().")
            return None
        if output_dir is not None and output_dir != self.session.run_dir:
            logger.warning("create_pdf_report(output_dir=...) is ignored now.")
        return self.session.render_pdf(
            report_template, page_size=page_size, logo_path=logo_path
        )

    # -- messages -----------------------------------------------------------
    def _emit(
        self,
        method: str,
        msg: str,
        report: bool | None,
        log: bool | None,
        popup: bool,
        popup_kind: str,
        dev_level: int,
    ) -> None:
        _report = self.report if report is None else report
        _log = self.logging if log is None else log

        if _report:
            getattr(self.log, method)(msg, stacklevel=_FORWARD + 1)
        elif _log:
            logger.log(dev_level, msg, stacklevel=_FORWARD + 1)
        if popup:
            getattr(self.notifier, popup_kind)(msg)

    def critical(self, msg, report=None, log=None, verbose=None, popup=False) -> None:
        self._emit("critical", msg, report, log, popup, "critical", logging.CRITICAL)

    def debug(self, msg, report=None, log=None, verbose=None, popup=False) -> None:
        # Old debug() went into the text report; debug now belongs in the dev log.
        self._emit("debug", msg, report, log, popup, "error", logging.DEBUG)

    def error(self, msg, report=None, log=None, verbose=None, popup=False) -> None:
        self._emit("error", msg, report, log, popup, "error", logging.ERROR)

    def exception(self, msg, report=None, log=None, verbose=None, popup=False) -> None:
        self._emit("exception", msg, report, log, popup, "error", logging.ERROR)

    def info(self, msg, report=None, log=None, verbose=None, popup=False) -> None:
        self._emit("info", msg, report, log, popup, "info", logging.INFO)

    def warning(self, msg, report=None, log=None, verbose=None, popup=False) -> None:
        self._emit("warning", msg, report, log, popup, "warning", logging.WARNING)

    def ask(
        self,
        msg: str,
        title: str | None = None,
        yes_text: str = "Yes",
        no_text: str = "No",
        default: bool = False,
        report: bool | None = None,
        log: bool | None = None,
        verbose: bool | None = None,
    ) -> bool:
        _report = self.report if report is None else report
        return self.notifier.ask(
            msg,
            title=title or "Input needed",
            yes_text=yes_text,
            no_text=no_text,
            default=default,
            run_log=self.log if _report else None,
        )

    # -- headings and dividers ----------------------------------------------
    def title(self, message: str) -> None:
        self.log.title(message, stacklevel=2)

    def subtitle(self, message: str) -> None:
        self.log.subtitle(message, stacklevel=2)

    def simple_title(self, message: str) -> None:
        self.log.simple_title(message, stacklevel=2)

    def highlight_error(self, message: str, is_critical: bool = False) -> None:
        self.log.highlight_error(message, is_critical, stacklevel=2)

    def highlight_titled_error(
        self, message: str, title: str = "COMPARISON FAILED", is_critical: bool = False
    ) -> None:
        self.log.highlight_titled_error(message, title, is_critical, stacklevel=2)

    def divider(self) -> None:
        self.log.divider(stacklevel=2)

    def separator(self) -> None:
        self.log.separator(stacklevel=2)

    def section(self) -> None:
        self.log.section(stacklevel=2)

    def error_divider(self) -> None:
        self.log.error_divider(stacklevel=2)

    def error_separator(self) -> None:
        self.log.error_separator(stacklevel=2)

    def error_section(self) -> None:
        self.log.error_section(stacklevel=2)
