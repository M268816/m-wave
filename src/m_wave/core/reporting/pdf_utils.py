# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH
# This tool was created with the help of AI.

# stdlib
from datetime import datetime
from enum import Enum
from pathlib import Path

# third-party
from reportlab.lib import colors

# local
from m_wave.core.reporting.pdf_styles import ColorPalette


# Formatting helpers
def thousands(value: float | None) -> str:
    """Format a number with thousands separators, or an em dash when absent."""
    if value is None:
        return "\u2014"
    return f"{value:,.0f}"


def percentage(value: float | None, decimals: int = 1) -> str:
    """Format a ratio already expressed in percent, e.g. 99.96 -> '99.96%'."""
    if value is None:
        return "\u2014"
    return f"{value:.{decimals}f}%"


def format_datetime(moment: datetime | None) -> str:
    """Render a timestamp in the Merck-style display format."""
    if moment is None:
        return "\u2014"
    return moment.strftime("%d-%b-%Y %H:%M:%S")


def shorten_path(path: Path | None, max_length: int = 128) -> str:
    """
    Render a file path compactly: keep the file name and enough of the tail of
    the parent folders to stay recognizable.
    """
    if path is None:
        return "\u2014"

    text = str(path)
    if len(text) <= max_length:
        return text

    return "\u2026" + text[-(max_length - 1) :]


class PDFReportStatus(str, Enum):
    """Overall outcome of the process the report describes."""

    PASS = "pass"
    FAIL = "fail"
    ERRORED = "errored"
    NONE = "none"

    @property
    def label(self) -> str:
        return {
            PDFReportStatus.PASS: "PASS",
            PDFReportStatus.FAIL: "FAIL",
            PDFReportStatus.ERRORED: "ERRORED",
            PDFReportStatus.NONE: "NO RESULT",
        }[self]

    @property
    def fill(self) -> colors.Color:
        return {
            PDFReportStatus.PASS: ColorPalette.PASS_FILL,
            PDFReportStatus.FAIL: ColorPalette.FAIL_FILL,
            PDFReportStatus.ERRORED: ColorPalette.WARN_FILL,
            PDFReportStatus.NONE: ColorPalette.PANEL,
        }[self]

    @property
    def edge(self) -> colors.Color:
        return {
            PDFReportStatus.PASS: ColorPalette.PASS_EDGE,
            PDFReportStatus.FAIL: ColorPalette.FAIL_EDGE,
            PDFReportStatus.ERRORED: ColorPalette.WARN_EDGE,
            PDFReportStatus.NONE: ColorPalette.NOTE_EDGE,
        }[self]

    @property
    def text(self) -> colors.Color:
        return {
            PDFReportStatus.PASS: ColorPalette.PASS_TEXT,
            PDFReportStatus.FAIL: ColorPalette.FAIL_TEXT,
            PDFReportStatus.ERRORED: ColorPalette.WARN_TEXT,
            PDFReportStatus.NONE: ColorPalette.SLATE,
        }[self]
