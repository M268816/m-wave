# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH
# This tool was created with the help of AI.

"""
Reporter: the one object a WavePack uses for all of its reporting.

The Reporter OWNS one of each reporting part (composition) and does nothing
else except start and finish runs:

    reporter.debug      DebugLog      -> for development and bug catching
    reporter.journal    Journal       -> for technical reviewers
    reporter.artifacts  Artifacts     -> handles comparison files for technical review
    reporter.pdf        PdfReport     -> handles the non-technical review report
    reporter.notifier   Notifier      -> modal notifications for the user
    reporter.report     ReportRequest -> name, ID, folder and start time of the current
                                         run

Example run: (Instanced in a WavePack controller):

    reporter.start_report("Example Comparison")
    try:
        pdf_template = processor.run(request)   # writes journal, artifacts, ...
        reporter.finish_report(pdf_template)    # saves the PDF, closes the journal
    except Exception as error:
        reporter.finish_report_with_error(error)   # ERRORED PDF, traceback to DebugLog

Report folder:
    reports/
        (<timestamp>)_<name>/
            journal.log      technical journal
            summary.pdf      non-technical summary
            artifacts/       comparison files or other process artifacts

Keep this class small. If a method here grows past ~10 lines, that work
probably belongs in one of the parts above.
"""

from __future__ import annotations

# stdlib
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

# local
from m_wave.core.context import USER
from m_wave.core.paths import PATHS
from m_wave.core.reporting.artifacts import Artifacts
from m_wave.core.reporting.debug_log import DebugLog
from m_wave.core.reporting.journal import Journal
from m_wave.core.reporting.notifier import Notifier
from m_wave.core.reporting.pdf_builder import PDFReportTemplate
from m_wave.core.reporting.pdf_report import ErrorPdfTemplate, PdfReport
from m_wave.core.reporting.pdf_utils import PDFReportStatus
from m_wave.core.utils import DATETIME_FORMAT, DATETIME_FORMAT_MERCK

if TYPE_CHECKING:
    import ttkbootstrap as tkb
    from ttkbootstrap.widgets.scrolled import ScrolledText

JOURNAL_FILENAME = "journal.log"
PDF_FILENAME = "summary.pdf"
ARTIFACTS_FOLDER = "artifacts"


@dataclass
class ReportRequest:
    """
    Report information payload.
    Use this to fill in a PDF template.
    """

    name: str
    id: str  # also the run folder name, shown on the PDF
    user: str
    started_at: datetime
    folder: Path

    @property
    def journal_path(self) -> Path:
        return self.folder / JOURNAL_FILENAME

    @property
    def pdf_path(self) -> Path:
        return self.folder / PDF_FILENAME

    @property
    def artifacts_folder(self) -> Path:
        return self.folder / ARTIFACTS_FOLDER

    @classmethod
    def create(cls, name: str, output_dir: Path) -> ReportRequest:
        """Make the ReportRequest and its output folder."""
        name = name.strip() or "Not Named"
        started_at = datetime.now().astimezone()
        safe_name = name.replace(" ", "_").replace("*", "")
        run_id = f"({started_at.strftime(DATETIME_FORMAT)})_{safe_name}"

        folder = output_dir / run_id
        folder.mkdir(parents=True, exist_ok=True)
        return cls(name, run_id, USER, started_at, folder)


class Reporter:
    def __init__(
        self, window: tkb.Window | None, logo_path: Path | None = None
    ) -> None:
        self.debug = DebugLog()
        self.journal = Journal()
        self.artifacts = Artifacts(self.journal)
        self.pdf = PdfReport(logo_path=logo_path)
        self.notifier = Notifier(window, self.journal)

        self.report: ReportRequest | None = None
        self._report_duration = 0.0  # for the run duration

    def display_journal_to(
        self, text_box: ScrolledText, show_time: bool, show_level: bool
    ) -> None:
        """
        Display the journal lines in a GUI text box. (ScrolledText)
        Call from the main thread.
        """
        self.journal.display_to(text_box, show_time, show_level)

    def start_report(self, name: str, output_dir: Path | None = None) -> ReportRequest:
        """
        Create the report folder, open journal.log and write the run header.
        """
        if self.report is not None:
            self.debug.warning(
                "start_report() called while report:'%s' was still open.",
                self.report.id,
            )
            self._close_report()

        self.report = ReportRequest.create(name, output_dir or PATHS.reports_dir)
        self._report_duration = time.perf_counter()

        self.journal.open_file(self.report.journal_path)
        self.artifacts.start(self.report.artifacts_folder)
        self.debug.info("===== REPORT STARTED: %s =====", self.report.id)

        self.journal.title(self.report.name)
        self.journal.info(f"Report ID:   {self.report.id}")
        self.journal.info(f"User:     {self.report.user}")
        self.journal.info(
            f"Started:  {self.report.started_at.strftime(DATETIME_FORMAT_MERCK)}"
        )
        self.journal.info(f"Folder:   {self.report.folder}")
        self.journal.divider()
        return self.report

    def finish_report(self, pdf_template: PDFReportTemplate) -> Path | None:
        """
        The report run completed. Save the PDF from ``pdf_template``, write the run
        footer, close journal.log. Returns the PDF path (None if the PDF failed).
        """
        if self.report is None:
            self.debug.warning("finish_report() called, but no run was started.")
            return None

        pdf_path = self.pdf.save(pdf_template, self.report.pdf_path)
        self._write_footer(pdf_template.status, pdf_path)
        self._close_report()
        return pdf_path

    def finish_report_with_error(self, error: BaseException) -> Path | None:
        """
        The run stopped with an error. Write the traceback to the DebugLog, a short
        explanation to the journal, save an ERRORED PDF, close journal.log.
        Call this from inside an ``except`` block.
        """
        self.debug.error("Run stopped by an error", error=error)
        if self.report is None:
            return None  # the error happened before start_report() finished

        error_text = f"{type(error).__name__}: {error}"
        self.journal.error_banner("Run stopped by an error")
        self.journal.error(error_text)
        self.journal.error("The full traceback is in the debug log.")

        template = ErrorPdfTemplate(
            title=self.report.name,
            report_id=self.report.id,
            user=self.report.user,
            created_date=self.report.started_at,
            status=PDFReportStatus.ERRORED,
            error_text=error_text,
        )
        pdf_path = self.pdf.save(template, self.report.pdf_path)
        self._write_footer(PDFReportStatus.ERRORED, pdf_path)
        self._close_report()
        return pdf_path

    def _write_footer(self, status: PDFReportStatus, pdf_path: Path | None) -> None:
        seconds = time.perf_counter() - self._report_duration

        self.journal.divider()
        self.journal.heading("Report finished")
        self.journal.info(f"Result:   {status.label}")
        if pdf_path is not None:
            self.journal.info(f"Summary:  {pdf_path.name}")
        else:
            self.journal.error(
                "Summary:  the PDF could not be created (see debug log)."
            )

        if self.artifacts.saved:
            self.journal.info(f"Artifacts ({len(self.artifacts.saved)}):")
            for artifact in self.artifacts.saved:
                self.journal.info(f"  - {artifact.name}: {artifact.description}")
        else:
            self.journal.info("Artifacts: none")

        self.journal.info(f"Duration: {seconds:.1f} s")
        self.journal.divider()

    def _close_report(self) -> None:
        if self.report is not None:
            self.debug.info("===== REPORT FINISHED: %s =====", self.report.id)
        self.journal.close_file()
        self.artifacts.finish()
        self.report = None
