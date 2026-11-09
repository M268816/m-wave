# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH
# This tool was created with the help of AI.

"""
MTL WavePack processor: the reference pattern for using the Reporter.

    reporter.journal    what a technical reviewer needs to follow the run
    reporter.artifacts  files a technical reviewer can open (before/after, CSVs)
    reporter.debug      detail only you need when debugging
    reporter.notifier   pop-ups / questions for the person at the screen
    (return value)      the PDF template: the summary for non-technical reviewers

The processor never imports tkinter or ttkbootstrap. Everything the user sees
goes through reporter.notifier, so the processor can be tested without a GUI.
"""

# stdlib
import csv
from pathlib import Path

# third party
# local
from m_wave.core.reporting.pdf_builder import PDFReportTemplate
from m_wave.core.reporting.pdf_utils import PDFReportStatus
from m_wave.core.reporting.reporter import Reporter

# local extension
from m_wave.extensions.mtl.function.extract import DataExtractor
from m_wave.extensions.mtl.pdf_template import (
    ComparisonPDFTemplate,
    DownloadPDFTemplate,
    ReportIssue,
)
from m_wave.extensions.mtl.utils.metadata import Metadata
from m_wave.extensions.mtl.utils.utils import MTLProcessorRequest, MTLUiPayload


class MTLProcessor:
    def __init__(self, reporter: Reporter) -> None:
        self.reporter = reporter
        self.journal = reporter.journal  # short names, used on almost every line
        self.debug = reporter.debug

        self.metadata = Metadata(self.reporter)
        self.extractor = DataExtractor(self.reporter, self.metadata)

    def _build_download_pdf(
        self,
        request: MTLProcessorRequest,
        status: PDFReportStatus,
        issues: list[ReportIssue],
    ) -> DownloadPDFTemplate:
        """
        Helps build and update the status of a MTLDownloadRequest
        """
        report_name = request.report_name or "Downloading MTL/CMD"
        return DownloadPDFTemplate(
            title=report_name,
            report_id="MTL/CMD Download",
            user=request.user,
            created_date=request.start_datetime,
            status=status,
            issues=issues,
        )

    def download_mtl(
        self, request: MTLProcessorRequest, ui: MTLUiPayload
    ) -> PDFReportTemplate:
        """
        Download the MTL/CMD directly from ManGo.
        """
        self.journal.title("DOWNLOADING THE MTL/CMD FROM MANGO")
        self.extractor.reset_report_issues()
        download_issues: list[ReportIssue] = []

        try:
            download_path = self.extractor.download_mtl()
            self.journal.subtitle("MTL/CMD SUCCESSFULLY DOWNLOADED")

            if download_path is not None:
                self.journal.info("Attempting to retrieve the last document revision.")
                ui.mtl_path.set(str(download_path))

                try:
                    revision = self.extractor.get_last_revision(download_path)
                    self.journal.info(f"Revision captured: {revision}")
                    ui.mtl_version.set(str(revision))
                    self.metadata.set_mtl_version(str(revision))
                except Exception as e:
                    e_text = (
                        "An unexpected error occurred while attempting to "
                        "update the UI with a new revision."
                    )
                    self.journal.error(e_text)
                    self.debug.error(e_text + ": %s", e)
                    issue = ReportIssue("Collecting Revision Data", e_text, "error")
                    download_issues.append(issue)
            else:
                self.journal.error(
                    "The download path couls not be captured while "
                    "attempting to download the MTL/CMD!"
                )
                issue = ReportIssue(
                    "Checking download path.", "No download path found", "error"
                )
                pdf = self._build_download_pdf(
                    request,
                    PDFReportStatus.FAIL,
                    download_issues + self.extractor.report_issues,
                )
                return pdf

            pdf = self._build_download_pdf(
                request,
                PDFReportStatus.PASS,
                download_issues + self.extractor.report_issues,
            )
            return pdf

        except Exception as e:
            e_text = (
                "An unexpected error occurred while attampting to download the MTL/CMD"
            )
            self.journal.error_banner(e_text)
            self.journal.error(f"{e}")
            self.debug.error(e_text + ": %s", e)
            pdf = self._build_download_pdf(
                request,
                PDFReportStatus.ERRORED,
                download_issues + self.extractor.report_issues,
            )
            return pdf

    # def run(self, request: MTLProcessorRequest) -> PDFReportTemplate:
    #     """
    #     Do processing work and return the filled-in PDF template.
    #     Raise an exception if something unexpected goes wrong. The controller
    #     catches it and the Reporter produces an ERRORED summary.
    #     """
    #     self.journal.title("This is an example WavePack")
    #
    #     # STEP 1: read the input ------------------------------------------------
    #     self.journal.heading("Step 1: Read the input file")
    #     self.journal.info(f"File: {request.file_path}")
    #     self.debug.debug(
    #         "Resolved input path: %s (exists=%s)",
    #         request.file_path.resolve(),
    #         request.file_path.exists(),
    #     )
    #
    #     if not request.file_path.exists():
    #         self.journal.error_banner("Input file not found")
    #         self.journal.error(f"No file at {request.file_path}")
    #         return self._make_template(PDFReportStatus.FAIL, rows=[])
    #
    #     # "Before" snapshot: the file exactly as it was given to us.
    #     self.reporter.artifacts.copy_in(
    #         request.file_path,
    #         f"before_{request.file_path.name}",
    #         "Input file as received",
    #     )
    #     rows = self._read_csv(request.file_path)
    #     self.journal.info(f"Read {len(rows):,} rows.")
    #
    #     if not rows:
    #         go_on = self.reporter.notifier.ask(
    #             "The file has no rows. Continue anyway?", default=False
    #         )
    #         if not go_on:
    #             self.journal.warning("Stopped by the user: the input file was empty.")
    #             return self._make_template(PDFReportStatus.FAIL, rows)
    #
    #     # STEP 2: format ---------------------------------------------------------
    #     self.journal.heading("Step 2: Format the data")
    #     formatted = [[cell.strip() for cell in row] for row in rows]
    #     changed = sum(1 for before, after in zip(rows, formatted) if before != after)
    #     self.journal.info(f"Trimmed spaces in {changed:,} rows.")
    #
    #     # "After" snapshot: the data as it will be compared.
    #     self.reporter.artifacts.save_csv(
    #         "after_formatting.csv", formatted, "Input file after formatting"
    #     )
    #
    #     # STEP 3: decide the result ----------------------------------------------
    #     self.journal.heading("Step 3: Result")
    #     status = PDFReportStatus.PASS
    #     self.journal.info(f"Result: {status.label}")
    #     return self._make_template(status, formatted)

    # ------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------
    def _read_csv(self, path: Path) -> list[list[str]]:
        with open(path, newline="", encoding="utf-8-sig") as file:
            rows = list(csv.reader(file))
        self.debug.debug("First row: %r", rows[0] if rows else None)
        return rows

    def _make_template(
        self, status: PDFReportStatus, rows: list[list[str]]
    ) -> PDFReportTemplate:
        """The PDF is built from data, never from journal lines."""
        report = self.reporter.report
        assert report is not None, (
            "The controller must call reporter.start_report() first."
        )

        return ComparisonPDFTemplate(
            title=report.name,
            report_id=report.id,
            user=report.user,
            created_date=report.started_at,
            status=status,
            subtitle="Just a little subtitle",
        )
