# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH
# This tool was created with the help of AI.

"""
PdfReport: saves a summary PDF for non-technical reviewers.

The layout lives in the pdf_* files:
    pdf_builder.py     page setup, header, footer  (PDFReportBuilder, PDFReportTemplate)
    pdf_components.py  building blocks (status banner, tables, metric cards)
    pdf_styles.py      fonts, colours, sizes
    pdf_utils.py       number/date formatting and PDFReportStatus

Each WavePack writes its own template (for example ExamplePDFReportTemplate)
that fills in the content. This file only adds two things on top of this system:

    PdfReport          saves a template to a file and never crashes the run
    ErrorPdfTemplate   a ready-made ERRORED summary, used by the Reporter when a
                       run stops with an error, so WavePacks do not need their own
"""

from __future__ import annotations

# stdlib
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

# third-party
from reportlab.platypus import Flowable, Spacer

# local
from m_wave.core.reporting.debug_log import DebugLog
from m_wave.core.reporting.pdf_builder import PDFReportBuilder, PDFReportTemplate
from m_wave.core.reporting.pdf_components import (
    note_box,
    section_heading,
    status_banner,
)
from m_wave.core.reporting.pdf_styles import Sizing, TextStyles


class PdfReport:
    def __init__(
        self,
        logo_path: Path | None = None,
        page_size: tuple[float, float] | None = None,
    ) -> None:
        self.builder = PDFReportBuilder(page_size=page_size, logo_path=logo_path)
        self._debug = DebugLog()

    def save(self, pdf_template: PDFReportTemplate, file_path: Path) -> Path | None:
        """
        Build the PDF from ``template`` and save it to ``file_path``.

        Returns the path, or None if the PDF could not be built. It never raises:
        a broken PDF must not hide the result of the comparison, which is
        already in the journal. The reason is written to the DebugLog.
        """
        try:
            self.builder.build(pdf_template, file_path)
        except Exception as error:
            self._debug.error("The PDF could not be built: %s", file_path, error=error)
            return None

        self._debug.info("PDF saved: %s (%s)", file_path, pdf_template.status.label)
        return file_path


@dataclass
class ErrorPdfTemplate(PDFReportTemplate):
    """
    Summary for a run that stopped with an error. Status should be ERRORED.

    ``error_text`` is shown to the reviewer, so keep it to one plain sentence
    (the Reporter uses "<ErrorType>: <message>").
    """

    error_text: str = ""

    @property
    def status_message(self) -> str:
        return (
            "The process stopped before it finished. "
            "No comparison result is available for this run."
        )

    def build_components(self, styles: TextStyles, width: float) -> list[Flowable]:
        return [
            status_banner(styles, self.status, self.status_message, width),
            Spacer(1, Sizing.GAP_SECTION),
            section_heading(styles, "What happened"),
            Spacer(1, 10),
            # escape(): ReportLab reads < and & as markup, error messages may contain them.
            note_box(styles, escape(self.error_text or "Unknown error."), width),
            Spacer(1, Sizing.GAP_SECTION),
            note_box(
                styles,
                "Technical details are in the journal.log in the same folder as this "
                "PDF. Please send that file with a support request.",
                width,
            ),
        ]
