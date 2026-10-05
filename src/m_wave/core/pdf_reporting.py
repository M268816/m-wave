# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH
# This tool was created with the help of AI.

"""
Generic ReportLab PDF reporting layer.

This module owns everything that is the same for every report:

    * the visual design tokens (colors, fonts, spacing)
    * the paragraph / table styles built from those tokens
    * reusable layout components (header, status banner, metric grid,
      section heading, data table, note box)
    * the document shell (page size, margins, repeating footer, page numbers)

A WavePack owns only two things:

    * a dataclass that extends ``PDFReportData``
    * that dataclass' ``build_elements()`` implementation, which returns the
      ordered list of ReportLab flowables for its own report body

Nothing in this module knows about any specific WavePack.
"""

from __future__ import annotations

# stdlib
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

# third party
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    HRFlowable,
    Image,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

# ---------------------------------------------------------------------------
# Design tokens
#
# These are the ReportLab equivalent of the CSS custom properties in the
# original HTML template. Change a value here and every report changes.
# ---------------------------------------------------------------------------


class Palette:
    """Report color tokens based on the supplied Merck color palette."""

    # Core brand colors
    BRAND = colors.HexColor("#503291")  # rich purple: headings and table headers
    BLUE = colors.HexColor("#0F69AF")  # rich blue: metadata and supporting text
    GREEN = colors.HexColor("#149B5F")  # rich green: successful outcomes
    RED = colors.HexColor("#E61E50")  # rich red: errors and failed outcomes
    MAGENTA = colors.HexColor("#EB3C96")  # vibrant magenta: secondary emphasis
    CYAN = colors.HexColor("#2DBECD")  # vibrant cyan: rules and primary accent
    VIBRANT_GREEN = colors.HexColor("#A5CD50")
    YELLOW = colors.HexColor("#FFC832")  # vibrant yellow: warnings

    # Softer supporting colors
    SENSITIVE_BLUE = colors.HexColor("#96D7D2")
    SENSITIVE_PINK = colors.HexColor("#FFC3CD")
    SENSITIVE_GREEN = colors.HexColor("#B4DC96")
    SENSITIVE_YELLOW = colors.HexColor("#FFDBC9")

    # Semantic aliases used throughout the reusable components
    INK = BRAND  # body text
    MUTED = BLUE  # subtitles, metadata, footer
    SLATE = BRAND  # note text
    ACCENT = CYAN  # header rule, metric top rule
    RULE = SENSITIVE_BLUE  # hairline table borders
    PANEL = SENSITIVE_BLUE  # metric card + note background
    ZEBRA = SENSITIVE_GREEN  # even table row fill
    WHITE = colors.white

    PASS_FILL = SENSITIVE_GREEN
    PASS_EDGE = GREEN
    PASS_TEXT = GREEN

    FAIL_FILL = SENSITIVE_PINK
    FAIL_EDGE = RED
    FAIL_TEXT = RED

    WARN_FILL = SENSITIVE_YELLOW
    WARN_EDGE = YELLOW
    WARN_TEXT = BRAND

    NOTE_EDGE = BLUE

    SEVERITY_ERROR = RED
    SEVERITY_WARNING = BRAND


class Metrics:
    """Spacing and sizing tokens, in ReportLab points."""

    PAGE_SIZE = A4
    PAGE_SIZE_LANDSCAPE = landscape(A4)

    MARGIN_TOP = 18 * mm
    MARGIN_BOTTOM = 18 * mm
    MARGIN_LEFT = 16 * mm
    MARGIN_RIGHT = 16 * mm

    # One consistent gap value used between every sibling element.
    GAP = 6
    GAP_SECTION = 18
    GAP_HEADING = 20

    ACCENT_RULE = 5  # header underline weight
    BAR_WIDTH = 2 * mm  # status banner / note left bar
    METRIC_RULE = 3  # metric card top rule

    CELL_PAD_X = 9
    CELL_PAD_Y = 8

    FOOTER_OFFSET = 10 * mm


# Base-14 fonts are embedded in every PDF reader, need no font files, and
# survive PyInstaller bundling without any extra data files.
FONT_BODY = "Helvetica"
FONT_BOLD = "Helvetica-Bold"


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
            PDFReportStatus.PASS: Palette.PASS_FILL,
            PDFReportStatus.FAIL: Palette.FAIL_FILL,
            PDFReportStatus.ERRORED: Palette.WARN_FILL,
            PDFReportStatus.NONE: Palette.PANEL,
        }[self]

    @property
    def edge(self) -> colors.Color:
        return {
            PDFReportStatus.PASS: Palette.PASS_EDGE,
            PDFReportStatus.FAIL: Palette.FAIL_EDGE,
            PDFReportStatus.ERRORED: Palette.WARN_EDGE,
            PDFReportStatus.NONE: Palette.NOTE_EDGE,
        }[self]

    @property
    def text(self) -> colors.Color:
        return {
            PDFReportStatus.PASS: Palette.PASS_TEXT,
            PDFReportStatus.FAIL: Palette.FAIL_TEXT,
            PDFReportStatus.ERRORED: Palette.WARN_TEXT,
            PDFReportStatus.NONE: Palette.SLATE,
        }[self]


# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------


class ReportStyles:
    """
    The report's typographic system.

    One instance is created per document and handed to every builder, so a
    WavePack never has to invent its own fonts, sizes, or colors.
    """

    def __init__(self) -> None:
        self.title = ParagraphStyle(
            name="ReportTitle",
            fontName=FONT_BOLD,
            fontSize=25,
            leading=28,
            textColor=Palette.BRAND,
        )

        self.subtitle = ParagraphStyle(
            name="ReportSubtitle",
            fontName=FONT_BODY,
            fontSize=10,
            leading=15,
            textColor=Palette.MUTED,
        )

        self.metadata = ParagraphStyle(
            name="ReportMetadata",
            fontName=FONT_BODY,
            fontSize=9,
            leading=13,
            textColor=Palette.MUTED,
        )

        self.heading = ParagraphStyle(
            name="SectionHeading",
            fontName=FONT_BOLD,
            fontSize=15,
            leading=19,
            textColor=Palette.BRAND,
        )

        self.body = ParagraphStyle(
            name="Body",
            fontName=FONT_BODY,
            fontSize=10,
            leading=15,
            textColor=Palette.INK,
        )

        self.note = ParagraphStyle(
            name="Note",
            fontName=FONT_BODY,
            fontSize=9,
            leading=14,
            textColor=Palette.SLATE,
        )

        self.status_label = ParagraphStyle(
            name="StatusLabel",
            fontName=FONT_BOLD,
            fontSize=15,
            leading=19,
        )

        self.status_body = ParagraphStyle(
            name="StatusBody",
            fontName=FONT_BODY,
            fontSize=10,
            leading=15,
        )

        self.metric_label = ParagraphStyle(
            name="MetricLabel",
            fontName=FONT_BODY,
            fontSize=8,
            leading=11,
            textColor=Palette.MUTED,
        )

        self.metric_value = ParagraphStyle(
            name="MetricValue",
            fontName=FONT_BOLD,
            fontSize=18,
            leading=21,
            textColor=Palette.BRAND,
        )

        self.table_header = ParagraphStyle(
            name="TableHeader",
            fontName=FONT_BOLD,
            fontSize=9,
            leading=12,
            textColor=Palette.WHITE,
        )

        self.table_header_right = ParagraphStyle(
            name="TableHeaderRight",
            parent=self.table_header,
            alignment=TA_RIGHT,
        )

        self.cell = ParagraphStyle(
            name="TableCell",
            fontName=FONT_BODY,
            fontSize=9,
            leading=12,
            textColor=Palette.INK,
        )

        self.cell_number = ParagraphStyle(
            name="TableCellNumber",
            parent=self.cell,
            alignment=TA_RIGHT,
        )

        self.cell_error = ParagraphStyle(
            name="TableCellError",
            parent=self.cell,
            fontName=FONT_BOLD,
            textColor=Palette.SEVERITY_ERROR,
        )

        self.cell_warning = ParagraphStyle(
            name="TableCellWarning",
            parent=self.cell,
            fontName=FONT_BOLD,
            textColor=Palette.SEVERITY_WARNING,
        )

        self.footer = ParagraphStyle(
            name="Footer",
            fontName=FONT_BODY,
            fontSize=9,
            leading=12,
            textColor=Palette.MUTED,
            alignment=TA_LEFT,
        )

    def severity_style(self, severity: str) -> ParagraphStyle:
        """Map a severity string onto the matching cell style."""
        key = (severity or "").strip().lower()
        if key in {"error", "fail", "critical"}:
            return self.cell_error
        if key in {"warning", "warn", "review"}:
            return self.cell_warning
        return self.cell


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


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


def shorten_path(path: Path | str | None, max_length: int = 64) -> str:
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


# ---------------------------------------------------------------------------
# Reusable layout components
#
# Each function returns a flowable (or a short list of them) so a WavePack can
# compose a report body without touching raw ReportLab table styling.
# ---------------------------------------------------------------------------


def _bar_panel(
    content: Sequence[Flowable],
    width: float,
    fill: colors.Color,
    edge: colors.Color,
) -> Table:
    """
    A panel with a solid colored bar down its left edge.

    This is the ReportLab equivalent of ``border-left: 6px solid`` with a
    tinted background. The bar is its own table cell rather than a drawn line,
    so it never bleeds outside the panel.
    """
    bar_width = Metrics.BAR_WIDTH

    panel = Table(
        [["", list(content)]],
        colWidths=[bar_width, width - bar_width],
    )

    panel.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), edge),
                ("BACKGROUND", (1, 0), (1, 0), fill),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (0, 0), 0),
                ("RIGHTPADDING", (0, 0), (0, 0), 0),
                ("TOPPADDING", (0, 0), (0, 0), 0),
                ("BOTTOMPADDING", (0, 0), (0, 0), 0),
                ("LEFTPADDING", (1, 0), (1, 0), 16),
                ("RIGHTPADDING", (1, 0), (1, 0), 16),
                ("TOPPADDING", (1, 0), (1, 0), 13),
                ("BOTTOMPADDING", (1, 0), (1, 0), 13),
            ]
        )
    )

    return panel


def report_header(
    styles: ReportStyles,
    title: str,
    subtitle: str | None,
    metadata: Sequence[tuple[str, str]],
    width: float,
    logo_path: Path | None = None,
) -> list[Flowable]:
    """
    The report masthead: title, optional subtitle, metadata lines, and the
    accent rule that closes the block.
    """
    block: list[Flowable] = [Paragraph(title, styles.title)]

    if subtitle:
        block.append(Spacer(1, 5))
        block.append(Paragraph(subtitle, styles.subtitle))

    if metadata:
        block.append(Spacer(1, 15))
        for label, value in metadata:
            block.append(Paragraph(f"{label}: {value}", styles.metadata))

    if logo_path is not None and Path(logo_path).exists():
        logo = _scaled_image(Path(logo_path), target_width=26 * mm)
        header = Table(
            [[block, logo]],
            colWidths=[width - 30 * mm, 30 * mm],
        )
        header.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (0, 0), "TOP"),
                    ("VALIGN", (1, 0), (1, 0), "TOP"),
                    ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )
        elements: list[Flowable] = [header]
    else:
        elements = list(block)

    elements.append(Spacer(1, 14))
    elements.append(
        HRFlowable(
            width="100%",
            thickness=Metrics.ACCENT_RULE,
            color=Palette.ACCENT,
            spaceBefore=0,
            spaceAfter=0,
        )
    )
    elements.append(Spacer(1, 22))

    return elements


def status_banner(
    styles: ReportStyles,
    status: PDFReportStatus,
    message: str,
    width: float,
) -> Flowable:
    """The PASS / FAIL / WARNING panel."""
    label_style = ParagraphStyle(
        name=f"StatusLabel-{status.value}",
        parent=styles.status_label,
        textColor=status.text,
    )
    body_style = ParagraphStyle(
        name=f"StatusBody-{status.value}",
        parent=styles.status_body,
        textColor=status.text,
    )

    content = [
        Paragraph(status.label, label_style),
        Spacer(1, 3),
        Paragraph(message, body_style),
    ]

    return _bar_panel(content, width, status.fill, status.edge)


def metric_grid(
    styles: ReportStyles,
    metrics: Sequence[tuple[str, str]],
    width: float,
    columns: int = 4,
) -> Flowable:
    """
    A row of metric cards: small uppercase label above a large value, with the
    accent rule across the top of each card.

    Explicit gap columns create the visual separation, because cell padding
    would sit inside the card background rather than between the cards.
    """
    if not metrics:
        return Spacer(1, 0)

    columns = max(1, min(columns, len(metrics)))
    gap = 10
    card_width = (width - gap * (columns - 1)) / columns

    def card(label: str, value: str) -> Table:
        inner = Table(
            [
                [Paragraph(label.upper(), styles.metric_label)],
                [Paragraph(value, styles.metric_value)],
            ],
            colWidths=[card_width],
        )
        inner.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), Palette.PANEL),
                    ("LINEABOVE", (0, 0), (-1, 0), Metrics.METRIC_RULE, Palette.ACCENT),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 12),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                    ("TOPPADDING", (0, 0), (-1, 0), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 2),
                    ("TOPPADDING", (0, 1), (-1, 1), 0),
                    ("BOTTOMPADDING", (0, 1), (-1, 1), 12),
                ]
            )
        )
        return inner

    rows: list[list] = []
    widths: list[float] = []

    for index in range(0, len(metrics), columns):
        chunk = list(metrics[index : index + columns])
        row: list = []
        for position, (label, value) in enumerate(chunk):
            if position:
                row.append("")
            row.append(card(label, value))
        while len(row) < columns * 2 - 1:
            row.append("")
        rows.append(row)

    for position in range(columns):
        if position:
            widths.append(gap)
        widths.append(card_width)

    grid = Table(rows, colWidths=widths, rowHeights=None)
    grid.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), gap),
            ]
        )
    )

    return grid


def section_heading(styles: ReportStyles, text: str) -> Flowable:
    """A section heading with the hairline rule beneath it."""
    heading = Table(
        [[Paragraph(text, styles.heading)]],
    )
    heading.setStyle(
        TableStyle(
            [
                ("LINEBELOW", (0, 0), (-1, -1), 2, Palette.RULE),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return heading


def data_table(
    styles: ReportStyles,
    headers: Sequence[str],
    rows: Sequence[Sequence[str | Paragraph]],
    width: float,
    column_ratios: Sequence[float] | None = None,
    right_aligned: Sequence[int] = (),
) -> Flowable:
    """
    A standard report table: brand-filled header row, hairline row borders,
    zebra striping, and a header that repeats on every page it spans.
    """
    if column_ratios is None:
        column_ratios = [1.0] * len(headers)

    total = sum(column_ratios)
    col_widths = [width * ratio / total for ratio in column_ratios]

    header_cells = [
        Paragraph(
            text,
            styles.table_header_right
            if index in right_aligned
            else styles.table_header,
        )
        for index, text in enumerate(headers)
    ]

    body_rows: list[list] = []
    for row in rows:
        cells: list = []
        for index, value in enumerate(row):
            if isinstance(value, Paragraph):
                cells.append(value)
            else:
                style = styles.cell_number if index in right_aligned else styles.cell
                cells.append(Paragraph(str(value), style))
        body_rows.append(cells)

    table = Table(
        [header_cells, *body_rows],
        colWidths=col_widths,
        repeatRows=1,
    )

    commands = [
        ("BACKGROUND", (0, 0), (-1, 0), Palette.BRAND),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), Metrics.CELL_PAD_X),
        ("RIGHTPADDING", (0, 0), (-1, -1), Metrics.CELL_PAD_X),
        ("TOPPADDING", (0, 0), (-1, -1), Metrics.CELL_PAD_Y),
        ("BOTTOMPADDING", (0, 0), (-1, -1), Metrics.CELL_PAD_Y),
        ("LINEBELOW", (0, 0), (-1, -1), 1, Palette.RULE),
    ]

    # Zebra striping. Row 0 is the header, so the first body row is row 1 and
    # the "even" rows of the original CSS are the odd ReportLab row indexes.
    for offset in range(len(body_rows)):
        if offset % 2 == 1:
            row_index = offset + 1
            commands.append(
                ("BACKGROUND", (0, row_index), (-1, row_index), Palette.ZEBRA)
            )

    table.setStyle(TableStyle(commands))
    return table


def note_box(styles: ReportStyles, text: str, width: float) -> Flowable:
    """A muted advisory panel, used for caveats and pointers to other files."""
    return _bar_panel(
        [Paragraph(text, styles.note)],
        width,
        Palette.PANEL,
        Palette.NOTE_EDGE,
    )


def empty_state(styles: ReportStyles, text: str) -> Flowable:
    """The message shown where a table would be if there were no rows."""
    return Paragraph(text, styles.body)


def _scaled_image(path: Path, target_width: float) -> Image:
    """
    Load an image and scale it proportionally to a target width.

    Dimensions are always computed from the real pixel size, so a replacement
    logo or a differently sized chart cannot overflow the frame.
    """
    from reportlab.lib.utils import ImageReader

    reader = ImageReader(str(path))
    pixel_width, pixel_height = reader.getSize()
    scale = target_width / float(pixel_width)

    return Image(
        str(path),
        width=target_width,
        height=pixel_height * scale,
    )


def chart_image(path: Path, width: float) -> Flowable:
    """Embed a generated chart, scaled to the frame width."""
    return _scaled_image(Path(path), target_width=width)


# ---------------------------------------------------------------------------
# Report data contract
# ---------------------------------------------------------------------------


@dataclass
class PDFReportData:
    """
    Fields every report carries, regardless of which WavePack produced it.

    A WavePack subclasses this, adds its own fields, and implements
    ``build_elements()``.
    """

    title: str
    report_id: str
    user: str
    created_date: datetime
    status: PDFReportStatus
    subtitle: str | None = None

    # Charts generated for this run, keyed by name. The builder turns these
    # into flowables; nothing here needs file URLs, because ReportLab reads
    # the files directly.
    chart_paths: dict[str, Path] = field(default_factory=dict)

    @property
    def metadata_rows(self) -> list[tuple[str, str]]:
        """Masthead metadata. Override to add WavePack-specific lines."""
        return [
            ("Report ID", self.report_id),
            ("Generated", format_datetime(self.created_date)),
            ("Generated by", self.user),
        ]

    @property
    def status_message(self) -> str:
        """One sentence explaining the status. Override per report type."""
        return {
            PDFReportStatus.PASS: "The process completed with no findings.",
            PDFReportStatus.FAIL: "Findings were recorded and should be reviewed.",
            PDFReportStatus.ERRORED: "The process did not complete successfully.",
            PDFReportStatus.NONE: "No result was recorded for this run.",
        }[self.status]

    def build_elements(
        self,
        styles: ReportStyles,
        width: float,
    ) -> list[Flowable]:
        """
        Return the report body as ReportLab flowables.

        ``width`` is the usable frame width in points. Use it for any table or
        panel so the layout adapts if the margins or page size change.

        This is the ReportLab counterpart of a Jinja template: the base class
        provides the document shell, the subclass provides the content.
        """
        raise NotImplementedError(
            f"{type(self).__name__} must implement build_elements()."
        )


# ---------------------------------------------------------------------------
# Document shell
# ---------------------------------------------------------------------------


class _ReportCanvas(Canvas):
    """
    Canvas that defers saving so the total page count is known.

    ReportLab cannot know "of Y" until the whole document has been laid out,
    so pages are buffered, then stamped with the footer and written out.
    """

    def __init__(self, *args, footer_left: str = "", **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._footer_left = footer_left
        self._saved_pages: list[dict] = []

    def showPage(self) -> None:
        self._saved_pages.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        total = len(self._saved_pages)
        for state in self._saved_pages:
            self.__dict__.update(state)
            self._draw_footer(total)
            super().showPage()
        super().save()

    def _draw_footer(self, total: int) -> None:
        self.saveState()
        self.setFont(FONT_BODY, 9)
        self.setFillColor(Palette.MUTED)

        baseline = Metrics.MARGIN_BOTTOM - Metrics.FOOTER_OFFSET

        if self._footer_left:
            self.drawString(Metrics.MARGIN_LEFT, baseline, self._footer_left)

        self.drawRightString(
            self._pagesize[0] - Metrics.MARGIN_RIGHT,
            baseline,
            f"Page {self._pageNumber} of {total}",
        )

        self.restoreState()


class PDFReportBuilder:
    """
    Builds a PDF from any ``PDFReportData`` subclass.

    The builder owns the page geometry, the repeating footer, and the document
    metadata. It asks the report data for its body and renders it.
    """

    def __init__(
        self,
        page_size: tuple[float, float] | None = None,
        logo_path: Path | None = None,
    ) -> None:
        self.page_size = page_size or Metrics.PAGE_SIZE
        self.logo_path = logo_path
        self.styles = ReportStyles()

    @property
    def frame_width(self) -> float:
        """Usable content width in points."""
        return self.page_size[0] - Metrics.MARGIN_LEFT - Metrics.MARGIN_RIGHT

    @property
    def frame_height(self) -> float:
        """Usable content height in points."""
        return self.page_size[1] - Metrics.MARGIN_TOP - Metrics.MARGIN_BOTTOM

    def build(self, report: PDFReportData, output_path: Path) -> Path:
        """
        Render ``report`` to ``output_path`` and return that path.

        Raises whatever ReportLab raises; the caller decides how to report it.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        document = BaseDocTemplate(
            str(output_path),
            pagesize=self.page_size,
            leftMargin=Metrics.MARGIN_LEFT,
            rightMargin=Metrics.MARGIN_RIGHT,
            topMargin=Metrics.MARGIN_TOP,
            bottomMargin=Metrics.MARGIN_BOTTOM,
            title=report.title,
            author=report.user,
            subject=report.subtitle or report.title,
            creator="Workbook Automation & Verification Engine",
        )

        frame = Frame(
            Metrics.MARGIN_LEFT,
            Metrics.MARGIN_BOTTOM,
            self.frame_width,
            self.frame_height,
            leftPadding=0,
            rightPadding=0,
            topPadding=0,
            bottomPadding=0,
            id="content",
        )

        document.addPageTemplates([PageTemplate(id="report", frames=[frame])])

        elements: list[Flowable] = []
        elements.extend(
            report_header(
                self.styles,
                title=report.title,
                subtitle=report.subtitle,
                metadata=report.metadata_rows,
                width=self.frame_width,
                logo_path=self.logo_path,
            )
        )
        elements.extend(report.build_elements(self.styles, self.frame_width))

        footer_left = f"{report.report_id}  |  {report.status.label}"

        document.build(
            elements,
            canvasmaker=lambda *args, **kwargs: _ReportCanvas(
                *args, footer_left=footer_left, **kwargs
            ),
        )

        return output_path


__all__ = [
    "FONT_BODY",
    "FONT_BOLD",
    "KeepTogether",
    "Metrics",
    "PDFReportBuilder",
    "PDFReportData",
    "PDFReportStatus",
    "PageBreak",
    "Palette",
    "Paragraph",
    "ReportStyles",
    "Spacer",
    "chart_image",
    "data_table",
    "empty_state",
    "format_datetime",
    "metric_grid",
    "note_box",
    "percentage",
    "report_header",
    "section_heading",
    "shorten_path",
    "status_banner",
    "thousands",
]
