# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH
# This tool was created with the help of AI.

"""
MTL WavePack pdf report layout.

This is the ReportLab equivalent of ``mtl_comparison_report_template.html``.
It owns the MTL report's data contract and its body layout; the document
shell, styles, and reusable components come from ``m_wave.core.pdf_report``.
"""

from __future__ import annotations

# stdlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# third party
from reportlab.platypus import Flowable, KeepTogether, Paragraph, Spacer

from m_wave.core.reporting.pdf_builder import PDFReportTemplate
from m_wave.core.reporting.pdf_components import (
    chart_image,
    data_metric_grid,
    data_table,
    empty_state,
    note_box,
    on_new_page,
    section_heading,
    status_banner,
)
from m_wave.core.reporting.pdf_styles import Sizing, TextStyles
from m_wave.core.reporting.pdf_utils import (
    PDFReportStatus,
    format_datetime,
    shorten_path,
    thousands,
)

# local


# How many individual differences are listed in the PDF. The full set belongs
# in the CSV export; a PDF with ten thousand mismatch rows helps nobody.
DIFFERENCE_SAMPLE_LIMIT = 15
SECURITY_SAMPLE_LIMIT = 15
KEY_SAMPLE_LIMIT = 15


# APPENDING


@dataclass
class ReportIssue:
    """
    A validation problem that stopped ot qualified the upsert.

    ''check'' names the guard that fired, ''detail'' is what the user needs to
    fix, ''severity'' drives the color in the findings table.

    severities as described in pdf_syles:
    critical, error, fail, warning, warn, review
    """

    check: str
    detail: str
    severity: str = "error"


@dataclass
class DownloadPDFTemplate(PDFReportTemplate):
    """
    The MTL Download report. A simple pass/fail PDF for the download attempt of the
    MTL/CMD.
    """

    issues: list[ReportIssue] = field(default_factory=list)

    def build_components(
        self,
        text_styles: TextStyles,
        width: float,
    ) -> list[Flowable]:
        """Assemble the append report body."""

        status_message = {
            PDFReportStatus.PASS: "The process completed downloading the MTL/CMD.",
            PDFReportStatus.FAIL: "Could not download the MTL/CMD. Review issues.",
            PDFReportStatus.ERRORED: "The process did not complete successfully.",
            PDFReportStatus.NONE: "No result was recorded for this run.",
        }[self.status]

        elements: list[Flowable] = [
            status_banner(text_styles, self.status, status_message, width),
            Spacer(1, Sizing.GAP_SECTION),
        ]

        elements.extend(self._issue_section(text_styles, width))
        elements.append(Spacer(1, Sizing.GAP_SECTION))

        return elements

    def _issue_section(
        self,
        text_styles: TextStyles,
        width: float,
    ) -> list[Flowable]:
        """
        Builds an issue section if issues are present within self.issues
        """

        heading = section_heading(text_styles, "Download Issues")

        if not self.issues:
            return [
                Spacer(1, Sizing.GAP_HEADING),
                KeepTogether(
                    [
                        heading,
                        Spacer(1, 10),
                        empty_state(
                            text_styles,
                            "No problems were found.",
                        ),
                    ]
                ),
            ]

        rows = [
            [
                issue.check,
                issue.detail,
                Paragraph(
                    issue.severity.capitalize(),
                    text_styles.severity_style(issue.severity),
                ),
            ]
            for issue in self.issues
        ]

        table = data_table(
            text_styles,
            headers=["Check Performed", "What was found", "Severity"],
            rows=rows,
            width=width,
            column_ratios=[1.8, 4.2, 1.0],
        )

        return [
            Spacer(1, Sizing.GAP_HEADING),
            heading,
            Spacer(1, 10),
            table,
        ]


@dataclass
class AppendPDFTemplate(PDFReportTemplate):
    """
    MTL append / upsert report.

    Inherits ``title``, ``report_id``, ``user``, ``created_date``, ``status``,
    ``subtitle``, and ``chart_paths`` from ``PDFReportData``.
    """

    mtl_source: Path | None = None
    pib_source: Path | None = None
    worksheet_name: str | None = None
    filter_string: str | None = None

    rows_in_mtl_before: int = 0
    rows_in_pib: int = 0
    rows_in_mtl_after: int = 0
    rows_updated: int = 0
    rows_appended: int = 0

    updated_keys: list[str] = field(default_factory=list)
    appended_keys: list[str] = field(default_factory=list)
    issues: list[ReportIssue] = field(default_factory=list)

    key_columns: list[str] = field(default_factory=list)
    artifacts: list[tuple[Path, str]] = field(default_factory=list)

    filter_action: str | None = None
    written_to_mtl: bool = False
    mtl_output_path: Path | None = None

    # -- derived values -----------------------------------------------------

    @property
    def rows_changed(self) -> int:
        return self.rows_updated + self.rows_appended

    @property
    def rows_untouched(self) -> int:
        """MTL rows the PI Builder file had nothing to say about."""
        return max(self.rows_in_mtl_before - self.rows_updated, 0)

    @property
    def row_delta(self) -> int:
        """Net change in table height. Should always equal rows_appended."""
        return self.rows_in_mtl_after - self.rows_in_mtl_before

    @property
    def row_count_reconciles(self) -> bool:
        """
        An upsert adds exactly one row per new key and changes no row count
        for an updated key. If this is False the numbers disagree with the
        arithmetic and the reader needs to know.
        """
        return self.row_delta == self.rows_appended

    # -- base-class hooks ---------------------------------------------------

    @property
    def metadata_rows(self) -> list[tuple[str, str]]:
        rows = [
            ("Report ID", self.report_id),
            ("Generated", format_datetime(self.created_date)),
            ("Generated by", self.user),
        ]

        if self.worksheet_name:
            rows.append(("Worksheet", self.worksheet_name))

        rows.append(("MTL source", shorten_path(self.mtl_source)))
        rows.append(("PI Builder source", shorten_path(self.pib_source)))

        if self.key_columns:
            rows.append(("Match keys", ", ".join(self.key_columns)))

        rows.append(("Filter", self.filter_string or "None"))

        return rows

    @property
    def status_message(self) -> str:
        if self.status is PDFReportStatus.PASS:
            target = "the MTL" if self.written_to_mtl else "the CSV export only"
            return (
                f"{thousands(self.rows_updated)} rows updated and "
                f"{thousands(self.rows_appended)} rows appended, written to "
                f"{target}."
            )

        if self.status is PDFReportStatus.FAIL:
            return (
                "The append was stopped before any data was written. "
                "Resolve the findings below and run it again."
            )

        if self.status is PDFReportStatus.ERRORED:
            return (
                "The append did not finish. The MTL may not reflect the "
                "counts below, so verify the output file before using it."
            )

        return "No append result was recorded for this run."

    # -- layout -------------------------------------------------------------

    def build_components(
        self,
        text_styles: TextStyles,
        width: float,
    ) -> list[Flowable]:
        """Assemble the append report body."""
        elements: list[Flowable] = [
            status_banner(text_styles, self.status, self.status_message, width),
            Spacer(1, Sizing.GAP_SECTION),
        ]

        elements.extend(self._summary_section(text_styles, width))
        elements.extend(self._issue_section(text_styles, width))
        elements.extend(self._row_accounting_section(text_styles, width))
        elements.extend(self._key_section(text_styles, width))
        elements.extend(self._artifact_section(text_styles, width))

        elements.append(Spacer(1, Sizing.GAP_SECTION))
        elements.append(note_box(text_styles, self._closing_note(), width))

        return elements

    # -- sections -----------------------------------------------------------

    def _summary_section(
        self,
        text_styles: TextStyles,
        width: float,
    ) -> list[Flowable]:
        metrics = [
            ("Rows updated", thousands(self.rows_updated)),
            ("Rows appended", thousands(self.rows_appended)),
            ("Rows unchanged", thousands(self.rows_untouched)),
            ("MTL rows after", thousands(self.rows_in_mtl_after)),
        ]

        return [
            section_heading(text_styles, "Summary"),
            Spacer(1, Sizing.GAP_SECTION),
            data_metric_grid(text_styles, metrics, width, columns=4),
            Spacer(1, Sizing.GAP),
        ]

    def _issue_section(
        self,
        text_styles: TextStyles,
        width: float,
    ) -> list[Flowable]:
        heading = section_heading(text_styles, "Findings")

        if not self.issues:
            return [
                Spacer(1, Sizing.GAP_HEADING),
                KeepTogether(
                    [
                        heading,
                        Spacer(1, 10),
                        empty_state(
                            text_styles,
                            "No problems were found. The column schema, the key "
                            "columns, and key uniqueness all passed, and the "
                            "result contained no duplicate keys.",
                        ),
                    ]
                ),
            ]

        rows = [
            [
                issue.check,
                issue.detail,
                Paragraph(
                    issue.severity.capitalize(),
                    text_styles.severity_style(issue.severity),
                ),
            ]
            for issue in self.issues
        ]

        table = data_table(
            text_styles,
            headers=["Check", "What was found", "Severity"],
            rows=rows,
            width=width,
            column_ratios=[1.8, 4.2, 1.0],
        )

        return [
            Spacer(1, Sizing.GAP_HEADING),
            heading,
            Spacer(1, 10),
            table,
        ]

    def _row_accounting_section(
        self,
        text_styles: TextStyles,
        width: float,
    ) -> list[Flowable]:
        rows = [
            ["MTL rows before the append", thousands(self.rows_in_mtl_before)],
            ["PI Builder rows supplied", thousands(self.rows_in_pib)],
            ["Rows updated in place", thousands(self.rows_updated)],
            ["Rows appended as new", thousands(self.rows_appended)],
            ["Rows left untouched", thousands(self.rows_untouched)],
            ["MTL rows after the append", thousands(self.rows_in_mtl_after)],
        ]

        table = data_table(
            text_styles,
            headers=["Category", "Rows"],
            rows=rows,
            width=width,
            column_ratios=[4.0, 1.0],
            right_aligned=(1,),
        )

        elements: list[Flowable] = [
            Spacer(1, Sizing.GAP_HEADING),
            section_heading(text_styles, "Row Accounting"),
            Spacer(1, 10),
            table,
        ]

        # Surface an arithmetic disagreement rather than letting the reader
        # discover it by adding up the table themselves.
        if not self.row_count_reconciles:
            elements.append(Spacer(1, Sizing.GAP))
            elements.append(
                Paragraph(
                    f"The table grew by {thousands(self.row_delta)} row(s) but "
                    f"{thousands(self.rows_appended)} row(s) were reported as "
                    "appended. Verify the output file before using it.",
                    text_styles.severity_style("error"),
                )
            )

        return elements

    def _key_section(
        self,
        text_styles: TextStyles,
        width: float,
    ) -> list[Flowable]:
        if not self.updated_keys and not self.appended_keys:
            return []

        rows: list[list[str]] = []

        for key in self.updated_keys[:KEY_SAMPLE_LIMIT]:
            rows.append([key, "Updated"])
        for key in self.appended_keys[:KEY_SAMPLE_LIMIT]:
            rows.append([key, "Appended"])

        table = data_table(
            text_styles,
            headers=["Record key", "Action"],
            rows=rows,
            width=width,
            column_ratios=[4.0, 1.4],
        )

        elements: list[Flowable] = [
            Spacer(1, Sizing.GAP_HEADING),
            section_heading(text_styles, "Changed Records"),
            Spacer(1, 10),
            table,
        ]

        hidden_updated = max(len(self.updated_keys) - KEY_SAMPLE_LIMIT, 0)
        hidden_appended = max(len(self.appended_keys) - KEY_SAMPLE_LIMIT, 0)

        if hidden_updated or hidden_appended:
            elements.append(Spacer(1, Sizing.GAP))
            elements.append(
                Paragraph(
                    f"{thousands(hidden_updated)} further updated row(s) and "
                    f"{thousands(hidden_appended)} further appended row(s) are "
                    "not listed here. The complete set is in the CSV exports.",
                    text_styles.metadata,
                )
            )

        return elements

    def _artifact_section(
        self,
        text_styles: TextStyles,
        width: float,
    ) -> list[Flowable]:
        rows = [[path.name, description] for path, description in self.artifacts]

        if self.filter_action:
            rows.append(["Table filter", self.filter_action])

        if not rows:
            return []

        table = data_table(
            text_styles,
            headers=["File", "What it contains"],
            rows=rows,
            width=width,
            column_ratios=[2.2, 4.0],
        )

        return [
            Spacer(1, Sizing.GAP_HEADING),
            section_heading(text_styles, "Generated Files"),
            Spacer(1, 10),
            table,
        ]

    def _closing_note(self) -> str:
        if self.status is not PDFReportStatus.PASS:
            return (
                "No changes were written to the MTL. The source MTL file was "
                "opened read-only, so it is unchanged on disk. Fix the "
                "findings above and run the append again."
            )

        if self.written_to_mtl and self.mtl_output_path:
            return (
                "The appended MTL was saved as a new file, "
                f"{self.mtl_output_path.name}. The original MTL was opened "
                "read-only and is unchanged. Review the appended workbook, "
                "then update the change log manually."
            )

        return (
            "The upsert completed and the result was exported to CSV. The "
            "original MTL was opened read-only and is unchanged. Review the "
            "CSV exports, then update the change log manually."
        )


# COMPARING


@dataclass
class ComparisonRecord:
    """A single field-level disagreement between the MTL and PIB datasets."""

    record_key: str
    column: str
    mtl_value: Any
    pib_value: Any
    severity: str = "error"

    @property
    def mtl_display(self) -> str:
        return "\u2014" if self.mtl_value is None else str(self.mtl_value)

    @property
    def pib_display(self) -> str:
        return "\u2014" if self.pib_value is None else str(self.pib_value)


@dataclass
class ColumnDifferenceSummary:
    """Aggregate difference counts for one compared column."""

    column: str
    difference_count: int
    missing_from_mtl: int = 0
    missing_from_pib: int = 0


@dataclass
class SecurityDifferenceRecord:
    """One principal (permission) that failed the security string comparison."""

    record_name: str
    column: str
    principal: str
    mtl_setting: str
    pib_setting: str
    matrix_setting: str
    finding: str
    severity: str = "error"


@dataclass
class SecurityComparisonSummary:
    """
    Security string results for the comparison report.

    ``parsing_enabled``: False when the user turned security string parsing off;
    the security columns were then excluded and left for manual review.
    ``columns``: security string columns found in both tables. Empty when the
    table has none.
    ``records_compared`` / ``failing_records``: counted per record, so they can
    be read alongside the data record counts.
    ``strings_compared``: individual security cells evaluated.
    ``mtl_pib_mismatches``: strings where MTL/CMD and PI disagree.
    ``matrix_failures``: strings where PI does not satisfy the security matrix.
    ``unevaluated_strings``: strings that could not be parsed, so the security
    result is incomplete.
    """

    parsing_enabled: bool = True
    columns: list[str] = field(default_factory=list)
    records_compared: int = 0
    failing_records: int = 0
    strings_compared: int = 0
    mtl_pib_mismatches: int = 0
    matrix_failures: int = 0
    unevaluated_strings: int = 0
    samples: list[SecurityDifferenceRecord] = field(default_factory=list)

    @property
    def performed(self) -> bool:
        return self.parsing_enabled and bool(self.columns)

    @property
    def passed(self) -> bool:
        return self.failing_records == 0 and self.unevaluated_strings == 0


@dataclass
class ComparisonPDFTemplate(PDFReportTemplate):
    """
    MTL vs PIB comparison report.

    Inherits ``title``, ``report_id``, ``user``, ``created_date``, ``status``,
    ``subtitle``, and ``chart_paths`` from ``PDFReportData``.
    """

    mtl_source: Path | None = None
    pib_source: Path | None = None
    records_compared: int = 0
    matching_records: int = 0
    non_matching_records: int = 0
    missing_from_mtl: int = 0
    missing_from_pib: int = 0
    column_summaries: list[ColumnDifferenceSummary] = field(default_factory=list)
    difference_samples: list[ComparisonRecord] = field(default_factory=list)
    csv_export_path: Path | None = None
    artifacts: list = field(default_factory=list)
    issues: list[ReportIssue] = field(default_factory=list)
    # None when no security result was supplied; the security section is omitted.
    security: SecurityComparisonSummary | None = None

    # -- derived values -----------------------------------------------------

    @property
    def security_performed(self) -> bool:
        return self.security is not None and self.security.performed

    @property
    def security_failing_records(self) -> int:
        return self.security.failing_records if self.security_performed else 0

    @property
    def missing_records(self) -> int:
        return self.missing_from_mtl + self.missing_from_pib

    @property
    def match_rate(self) -> float | None:
        if not self.records_compared:
            return None
        return self.matching_records / self.records_compared * 100.0

    # -- base-class hooks ---------------------------------------------------

    @property
    def metadata_rows(self) -> list[tuple[str, str]]:
        """Masthead metadata, extended with the two compared sources."""
        return [
            ("Report ID", self.report_id),
            ("Generated", format_datetime(self.created_date)),
            ("Generated by", self.user),
            ("MTL source", shorten_path(self.mtl_source)),
            ("PIB source", shorten_path(self.pib_source)),
        ]

    @property
    def status_message(self) -> str:
        if self.status is PDFReportStatus.PASS:
            return (
                "The datasets matched according to the configured comparison rules."
                f"{self._security_pass_suffix()}"
            )
        if self.status is PDFReportStatus.FAIL:
            return self._failure_message()
        if self.status is PDFReportStatus.ERRORED:
            return "The comparison did not finish. Results below may be incomplete."
        return "No comparison result was recorded for this run."

    def _failure_message(self) -> str:
        """Name each failing area, so a security-only failure is never "0 records"."""
        parts: list[str] = []
        if self.non_matching_records:
            parts.append(f"{thousands(self.non_matching_records)} data record(s)")
        if self.security_failing_records:
            parts.append(
                f"{thousands(self.security_failing_records)} security record(s)"
            )

        if not parts:
            return "The comparison failed. Review the findings below."
        return f"{' and '.join(parts)} failed comparison and should be reviewed."

    def _security_pass_suffix(self) -> str:
        if self.security is None:
            return ""
        if not self.security.parsing_enabled:
            return (
                " Security string parsing was turned off, so security columns "
                "require manual review."
            )
        if self.security.columns:
            return " Security strings matched and satisfied the security matrix."
        return ""

    # -- layout -------------------------------------------------------------

    def build_components(
        self,
        text_styles: TextStyles,
        width: float,
    ) -> list[Flowable]:
        """
        Assemble the MTL report body.

        Page flow, for reviewers reading top to bottom:
            1. Result and summary (the first page stands on its own).
            2. Generated files.
            3. Data differences by column (chart and breakdown).
            4. Record difference sample.
            5. Security string comparison summary.
            6. Security difference sample.
            7. Record counts, closing note, and processor issues.

        Each numbered block starts on a new page. Blocks with no content are
        omitted along with their page break, so no blank pages are produced.
        Record differences come before security strings because they carry
        more weight for validation.
        """
        first_page: list[Flowable] = [
            status_banner(text_styles, self.status, self.status_message, width),
            Spacer(1, Sizing.GAP_SECTION),
            *self._summary_section(text_styles, width),
        ]

        column_breakdown = [
            *self._chart_section(text_styles, width),
            *self._column_section(text_styles, width),
        ]

        closing: list[Flowable] = [
            *self._record_count_section(text_styles, width),
            Spacer(1, Sizing.GAP_SECTION),
            note_box(text_styles, self._closing_note(), width),
            Spacer(1, Sizing.GAP_SECTION),
            *self._issue_section(text_styles, width),
        ]

        return [
            *first_page,
            *on_new_page(self._artifact_section(text_styles, width)),
            *on_new_page(column_breakdown),
            *on_new_page(self._difference_section(text_styles, width)),
            *on_new_page(self._security_section(text_styles, width)),
            *on_new_page(self._security_difference_section(text_styles, width)),
            *on_new_page(closing),
        ]

    # -- sections -----------------------------------------------------------

    def _issue_section(
        self,
        text_styles: TextStyles,
        width: float,
    ) -> list[Flowable]:
        """
        Builds an issue section if issues are present within self.issues
        """

        heading = section_heading(text_styles, "Comparison Processor Issues")

        if not self.issues:
            return [
                Spacer(1, Sizing.GAP_HEADING),
                KeepTogether(
                    [
                        heading,
                        Spacer(1, 10),
                        empty_state(
                            text_styles,
                            "No problems were found.",
                        ),
                    ]
                ),
            ]

        rows = [
            [
                issue.check,
                issue.detail,
                Paragraph(
                    issue.severity.capitalize(),
                    text_styles.severity_style(issue.severity),
                ),
            ]
            for issue in self.issues
        ]

        table = data_table(
            text_styles,
            headers=["Check Performed", "What was found", "Severity"],
            rows=rows,
            width=width,
            column_ratios=[1.8, 4.2, 1.0],
        )

        return [
            Spacer(1, Sizing.GAP_HEADING),
            heading,
            Spacer(1, 10),
            table,
        ]

    def _summary_section(
        self,
        text_styles: TextStyles,
        width: float,
    ) -> list[Flowable]:
        metrics = [
            ("Records compared", thousands(self.records_compared)),
            ("Matching records", thousands(self.matching_records)),
            ("Data records failing", thousands(self.non_matching_records)),
            ("Missing records", thousands(self.missing_records)),
        ]

        elements: list[Flowable] = [
            section_heading(text_styles, "Summary"),
            Spacer(1, Sizing.GAP_SECTION),
            data_metric_grid(text_styles, metrics, width, columns=4),
            Spacer(1, Sizing.GAP),
        ]

        if self.security_performed and self.security is not None:
            elements.extend(
                [
                    data_metric_grid(
                        text_styles,
                        self._security_metrics(self.security),
                        width,
                        columns=4,
                    ),
                    Spacer(1, Sizing.GAP),
                ]
            )

        return elements

    @staticmethod
    def _security_metrics(security: SecurityComparisonSummary) -> list[tuple[str, str]]:
        return [
            ("Security records checked", thousands(security.records_compared)),
            ("Security records failing", thousands(security.failing_records)),
            ("MTL/CMD vs PI mismatches", thousands(security.mtl_pib_mismatches)),
            ("Security matrix failures", thousands(security.matrix_failures)),
        ]

    def _chart_section(
        self,
        text_styles: TextStyles,
        width: float,
    ) -> list[Flowable]:
        path = self.chart_paths.get("differences_by_column")
        if path is None or not path.exists():
            return []

        return [
            Spacer(1, Sizing.GAP_HEADING),
            section_heading(text_styles, "Differences by Column"),
            Spacer(1, Sizing.GAP_SECTION),
            chart_image(path, width),
            Spacer(1, Sizing.GAP),
        ]

    def _column_section(
        self,
        text_styles: TextStyles,
        width: float,
    ) -> list[Flowable]:
        if not self.column_summaries:
            return []

        rows = [
            [
                summary.column,
                thousands(summary.difference_count),
                thousands(summary.missing_from_mtl),
                thousands(summary.missing_from_pib),
            ]
            for summary in self.column_summaries
        ]

        table = data_table(
            text_styles,
            headers=["Column", "Differences", "Missing from MTL", "Missing from PIB"],
            rows=rows,
            width=width,
            column_ratios=[3.0, 1.4, 1.6, 1.6],
            right_aligned=(1, 2, 3),
        )

        return [
            Spacer(1, Sizing.GAP_HEADING),
            section_heading(text_styles, "Column Difference Breakdown"),
            Spacer(1, 10),
            table,
        ]

    def _artifact_section(
        self,
        text_styles: TextStyles,
        width: float,
    ) -> list[Flowable]:
        if not self.artifacts:
            return []

        rows = [
            [
                artifact.name,
                artifact.description,
            ]
            for artifact in self.artifacts
        ]

        table = data_table(
            text_styles,
            headers=["Name", "Description"],
            rows=rows,
            width=width,
            column_ratios=[1.0, 2.0],
            right_aligned=(),
        )

        return [
            Spacer(1, Sizing.GAP_HEADING),
            section_heading(text_styles, "Collected Artifacts (Generated Files)"),
            Spacer(1, 10),
            table,
        ]

    def _difference_section(
        self,
        text_styles: TextStyles,
        width: float,
    ) -> list[Flowable]:
        heading = section_heading(text_styles, "Record Difference Sample")

        if not self.difference_samples:
            return [
                Spacer(1, Sizing.GAP_HEADING),
                KeepTogether(
                    [
                        heading,
                        Spacer(1, 10),
                        empty_state(text_styles, "No differences were found."),
                    ]
                ),
            ]

        shown = self.difference_samples[:DIFFERENCE_SAMPLE_LIMIT]

        rows = [
            [
                record.record_key,
                record.column,
                record.mtl_display,
                record.pib_display,
                Paragraph(
                    record.severity.capitalize(),
                    text_styles.severity_style(record.severity),
                ),
            ]
            for record in shown
        ]

        table = data_table(
            text_styles,
            headers=["Record key", "Column", "MTL value", "PIB value", "Severity"],
            rows=rows,
            width=width,
            column_ratios=[1.6, 1.6, 1.5, 1.5, 1.0],
        )

        elements: list[Flowable] = [
            Spacer(1, Sizing.GAP_HEADING),
            heading,
            Spacer(1, 10),
            table,
        ]

        remaining = len(self.difference_samples) - len(shown)
        if remaining > 0:
            elements.append(Spacer(1, Sizing.GAP))
            elements.append(
                Paragraph(
                    f"Showing the first {thousands(len(shown))} of "
                    f"{thousands(len(self.difference_samples))} differences. "
                    f"{thousands(remaining)} further differences are in the "
                    "CSV export.",
                    text_styles.metadata,
                )
            )

        return elements

    def _security_section(
        self,
        text_styles: TextStyles,
        width: float,
    ) -> list[Flowable]:
        """Security string summary: what was checked and how it went."""
        security = self.security
        if security is None:
            return []

        heading = section_heading(text_styles, "Security String Comparison")

        if not security.parsing_enabled:
            message = (
                "Security string parsing was turned off for this comparison. "
                "Security string columns were excluded and must be reviewed "
                "manually."
            )
            return self._security_note(heading, text_styles, message)

        if not security.columns:
            return self._security_note(
                heading,
                text_styles,
                "This table has no security string columns to compare.",
            )

        rows = [
            ["Security columns compared", ", ".join(security.columns)],
            ["Security strings evaluated", thousands(security.strings_compared)],
            ["Records checked", thousands(security.records_compared)],
            ["Records failing", thousands(security.failing_records)],
            [
                "MTL/CMD and PI strings that differ",
                thousands(security.mtl_pib_mismatches),
            ],
            [
                "PI strings failing the security matrix",
                thousands(security.matrix_failures),
            ],
            [
                "Strings that could not be evaluated",
                thousands(security.unevaluated_strings),
            ],
        ]

        table = data_table(
            text_styles,
            headers=["Category", "Result"],
            rows=rows,
            width=width,
            column_ratios=[4.0, 2.0],
            right_aligned=(1,),
        )

        elements: list[Flowable] = [
            Spacer(1, Sizing.GAP_HEADING),
            heading,
            Spacer(1, 10),
            table,
        ]

        if security.unevaluated_strings:
            elements.append(Spacer(1, Sizing.GAP))
            elements.append(
                Paragraph(
                    f"{thousands(security.unevaluated_strings)} security string(s) "
                    "could not be evaluated, so the security result is incomplete. "
                    "See Comparison Processor Issues.",
                    text_styles.severity_style("error"),
                )
            )
        elif security.passed:
            elements.append(Spacer(1, Sizing.GAP))
            elements.append(
                empty_state(
                    text_styles,
                    "All security strings matched and satisfied the security matrix.",
                )
            )

        return elements

    @staticmethod
    def _wrappable_setting(setting: str) -> str:
        """
        Let long permission strings such as A(r,w,rd,wd,d,x,a,s,so,an) wrap at
        commas instead of being split mid-token in narrow table columns.
        """
        return setting.replace(",", ", ")

    @staticmethod
    def _security_note(
        heading: Flowable, text_styles: TextStyles, message: str
    ) -> list[Flowable]:
        return [
            Spacer(1, Sizing.GAP_HEADING),
            KeepTogether([heading, Spacer(1, 10), empty_state(text_styles, message)]),
        ]

    def _security_difference_section(
        self,
        text_styles: TextStyles,
        width: float,
    ) -> list[Flowable]:
        """Sample of failing permissions; the full set is in the security CSV."""
        if not self.security_performed or self.security is None:
            return []

        samples = self.security.samples
        if not samples:
            return []

        shown = samples[:SECURITY_SAMPLE_LIMIT]
        rows = [
            [
                record.record_name,
                record.column,
                record.principal,
                self._wrappable_setting(record.mtl_setting),
                self._wrappable_setting(record.pib_setting),
                self._wrappable_setting(record.matrix_setting),
                Paragraph(record.finding, text_styles.severity_style(record.severity)),
            ]
            for record in shown
        ]

        table = data_table(
            text_styles,
            headers=[
                "Record",
                "Column",
                "Permission",
                "MTL/CMD",
                "PI",
                "Matrix",
                "Finding",
            ],
            rows=rows,
            width=width,
            column_ratios=[1.4, 1.6, 1.4, 1.2, 1.2, 1.2, 1.5],
        )

        elements: list[Flowable] = [
            Spacer(1, Sizing.GAP_HEADING),
            section_heading(text_styles, "Security Difference Sample"),
            Spacer(1, 10),
            table,
        ]

        remaining = len(samples) - len(shown)
        if remaining > 0:
            elements.append(Spacer(1, Sizing.GAP))
            elements.append(
                Paragraph(
                    f"Showing the first {thousands(len(shown))} of "
                    f"{thousands(len(samples))} security differences. "
                    f"{thousands(remaining)} further differences are in "
                    "compared_security_strings.csv.",
                    text_styles.metadata,
                )
            )

        return elements

    def _record_count_section(
        self,
        text_styles: TextStyles,
        width: float,
    ) -> list[Flowable]:
        rows = [
            ["Records compared", thousands(self.records_compared)],
            ["Matching records", thousands(self.matching_records)],
            ["Data records failing", thousands(self.non_matching_records)],
            ["Missing from MTL", thousands(self.missing_from_mtl)],
            ["Missing from PIB", thousands(self.missing_from_pib)],
        ]

        if self.security_performed and self.security is not None:
            rows.extend(
                [
                    [
                        "Security records checked",
                        thousands(self.security.records_compared),
                    ],
                    [
                        "Security records failing",
                        thousands(self.security.failing_records),
                    ],
                ]
            )

        table = data_table(
            text_styles,
            headers=["Category", "Count"],
            rows=rows,
            width=width,
            column_ratios=[4.0, 1.0],
            right_aligned=(1,),
        )

        return [
            Spacer(1, Sizing.GAP_HEADING),
            section_heading(text_styles, "Record Counts"),
            Spacer(1, 10),
            table,
        ]

    def _closing_note(self) -> str:
        note = (
            "This PDF lists a sample of differences so it stays readable. "
            "The complete difference set is available in the accompanying "
            "CSV export"
        )
        note = (
            f"{note}: {self.csv_export_path.name}."
            if self.csv_export_path
            else f"{note}."
        )

        if self.security_performed:
            note += (
                " Every compared security permission is listed in "
                "compared_security_strings.csv."
            )
        return note
