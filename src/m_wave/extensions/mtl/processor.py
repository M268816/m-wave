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
from typing import Any

# third party
# local
from m_wave.core.reporting.pdf_builder import PDFReportTemplate
from m_wave.core.reporting.pdf_utils import PDFReportStatus
from m_wave.core.reporting.reporter import Reporter

# local extension
from m_wave.extensions.mtl.format.formatting import Formatting
from m_wave.extensions.mtl.format.sorting import Sorting
from m_wave.extensions.mtl.function.compare import Comparisons
from m_wave.extensions.mtl.function.extract import DataExtractor
from m_wave.extensions.mtl.pdf_template import (
    ComparisonPDFTemplate,
    DownloadPDFTemplate,
    ReportIssue,
)
from m_wave.extensions.mtl.utils.metadata import Metadata
from m_wave.extensions.mtl.utils.utils import (
    MTLEnvironmentTypes,
    MTLProcessorRequest,
    MTLUiPayload,
)


class MTLProcessor:
    def __init__(self, reporter: Reporter) -> None:
        self.reporter = reporter
        self.journal = reporter.journal  # short names, used on almost every line
        self.notify = reporter.notifier
        self.debug = reporter.debug

        self.metadata = Metadata(self.reporter)
        self.compare = Comparisons(self.reporter, self.metadata)
        self.extractor = DataExtractor(self.reporter, self.metadata)
        self.formatter = Formatting(self.reporter, self.metadata)
        self.sorter = Sorting(self.reporter, self.metadata)

    def _build_download_pdf(
        self,
        request: MTLProcessorRequest,
        status: PDFReportStatus,
        issues: list[ReportIssue],
    ) -> DownloadPDFTemplate:
        """
        Helps build and update the status of a MTLDownloadRequest
        """
        report_id = request.report_name or "No ID Needed"
        return DownloadPDFTemplate(
            title="MTL/CMD Download",
            report_id=report_id,
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
        self.extractor.report_issues.clear()
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

    def _build_comparison_pdf(
        self,
        request: MTLProcessorRequest,
        status: PDFReportStatus,
        issues: list[ReportIssue],
        csv_export_path: Path = Path(),
        comparison_fields: dict[str, Any] | None = None,
    ) -> ComparisonPDFTemplate:
        """
        Helps build and update the status of a MTLDownloadRequest
        """
        _comparison_fields = comparison_fields if comparison_fields is not None else {}
        return ComparisonPDFTemplate(
            title="MTL vs PI Builder Comparison Report",
            subtitle=(
                "Field-level comparison of the Master Tag List "
                "against the PI Builder input."
            ),
            report_id=str(request.report_name),
            status=status,
            created_date=request.start_datetime,
            mtl_source=request.mtl_file_path,
            pib_source=request.pib_file_path,
            csv_export_path=csv_export_path,
            user=request.user,
            issues=issues,
            **_comparison_fields,
        )

    def run_comparison(
        self, request: MTLProcessorRequest, ui: MTLUiPayload
    ) -> PDFReportTemplate:
        """
        Given a ProcessorRequest and UiPayload, this processor will run a comparison
        of a supplied MTL/CMD, and PI Builder file.
        """
        comparison_issues: list[ReportIssue] = []
        try:
            self.journal.title(
                f"COMPARISON STARTED FOR WORKSHEET: {request.mtl_worksheet_name}"
            )
            self.journal.subtitle(
                f"THIS REPROT WAS GENERATED BY: {request.user} "
                f" ON {request.start_datetime}"
            )
            env = (
                "THE SAME"
                if request.env_types == MTLEnvironmentTypes.SAME
                else "A DIFFERENT"
            )
            self.journal.subtitle(
                f"THIS COMPARISON WAS PROCESSED AGAINST {env} ENVIRONMENT."
            )
            if not request.filter:
                self.journal.subtitle("THIS REPORT DID NOT USE A FILTER")
            else:
                self.journal.subtitle(f'THIS REPORT USED "{request.filter}" TO FILTER:')
                self.journal.subtitle(f"{request.mtl_worksheet_name}")

            if not self.metadata.can_compare_worksheet():
                self.journal.warning(
                    "This table does not yet have the capability to process data."
                )
                return self._build_comparison_pdf(
                    request, PDFReportStatus.ERRORED, comparison_issues
                )

            # Extraction Phase
            self.journal.heading("Extracting the Data Table from the MTL Worksheet.")
            mtl_df = self.extractor.extract_mtl_table(request.mtl_file_path)
            self.journal.heading("Extracting the Data Table from the PI Builder CSV.")
            pib_df = self.extractor.extract_pib_csv(
                request.pib_file_path, request.filter
            )

            if not self.extractor.could_extract(mtl_df, pib_df):
                self.journal.warning("Could not extract data sets!")
                self.notify.warning("Could not extract data sets!")
                return self._build_comparison_pdf(
                    request, PDFReportStatus.ERRORED, comparison_issues
                )

            # Capture data frames before formatting
            self.reporter.artifacts.save_csv(
                "mtl_before_formatting",
                mtl_df,
                "The MTL/CMD extracted data before formating for comparison.",
            )
            self.reporter.artifacts.save_csv(
                "pib_before_formatting",
                pib_df,
                "The PI Builder extracted data before formatting for comparison.",
            )

            # Formatting Phase
            self.journal.heading("Formatting the MTL data.")
            self.formatter.format(mtl_df)
            self.journal.heading("Formatting the PI Builder data.")
            self.formatter.format(pib_df)

            # Conform Columns
            self.journal.heading("Conforming columns.")
            self.journal.info(
                "Columns will adjust to use the MTL/CMD at the one source of truth"
            )
            self.journal.info(
                "PI Builder columns that do not exist within the MTL/CMD "
                "will be dropped, and columns that are missing will "
                "cause an error."
            )
            mtl_df, pib_df = self.formatter.conform_columns(mtl_df, pib_df)

            if mtl_df.empty or pib_df.empty:
                self.journal.error_banner("CANNOT CONFORM COLUMNS")
                msg = (
                    "Could not align columns between the data sets. Process stopping. "
                    "Check that you are using the correct PI Builder CSV, or have "
                    "selected the correct MTL/CSV worksheet in the process options."
                )
                self.journal.error(msg)
                self.notify.error(msg, "Cannot conform data columns.")
                return self._build_comparison_pdf(
                    request, PDFReportStatus.ERRORED, comparison_issues
                )

            # Filtering Phase
            if request.filter:
                self.journal.heading("Filter Detected")
                self.journal.info(f"Filter: {request.filter}")
                self.journal.info("Filtering the MTL/CMD data.")
                mtl_df = self.formatter.filter_by_string(mtl_df, request.filter)
                self.journal.info("filtering the PI Builder data.")
                pib_df = self.formatter.filter_by_string(pib_df, request.filter)

                if mtl_df.empty or pib_df.empty:
                    msg = "Filtering the data returned an empty table."
                    self.journal.warning(msg)
                    self.notify.warning(msg)
                    msg = (
                        "This may not be an error, but a bad filter string or "
                        "an incomplete PI Builder export file. Check your "
                        "logs for errors, change your filter string, or "
                        "attempt anther PI Builder export with an updated PI filter."
                    )
                    self.journal.warning(msg)
                    self.notify.warning(msg)

            # Sorting Phase
            self.journal.heading("Sorting the data tables.")
            self.journal.info("Sorting will attempt to align to the MTL format.")
            self.journal.info("Sorting the MTL data.")
            mtl_df = self.sorter.sort(mtl_df)
            self.journal.info("Sorting the PI Builder data.")
            pib_df = self.sorter.sort(pib_df)
            if mtl_df.empty or pib_df.empty:
                msg = (
                    "Could not sort the data tables, check your logs. "
                    "for errors. Stopping Process."
                )
                self.journal.error(msg)
                self.notify.error(msg, "Could not sort data.")
                return self._build_comparison_pdf(
                    request, PDFReportStatus.ERRORED, comparison_issues
                )

            # Snapshots after formatting
            self.journal.info("Formatting Completed!")
            self.journal.heading("Collecting data snapshot after formatting steps.")
            self.reporter.artifacts.save_csv(
                "mtl_after_formatting",
                mtl_df,
                "The MTL/CMD extracted data after formatting for comparison.",
            )
            self.reporter.artifacts.save_csv(
                "pib_after_formatting",
                mtl_df,
                "The PI Builder extracted data after formatting for comparison.",
            )

            # Comparison Phase
            self.journal.heading("Comparing MTL and PI Builder tables.")
            use_exclusions = request.env_types == MTLEnvironmentTypes.DIFF
            self.compare.compare(
                mtl_df,
                pib_df,
                request.mtl_file_path,
                request.pib_file_path,
                use_exclusions,
                self.sorter.sort,
            )
            comparison_issues = comparison_issues + self.compare.comparison_issues
            self.compare.comparison_issues.clear()

            return self._build_comparison_pdf(
                request,
                self.compare.pdf_report_status,
                comparison_issues,
                self.compare.comparison_export_path,
                self.compare.comparison_fields,
            )

        except Exception as e:
            self.debug.debug("Could not run comparison: %s", e)
            self.journal.error("Could not run comparson")
            return self._build_comparison_pdf(
                request, PDFReportStatus.ERRORED, comparison_issues
            )

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
