# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH
# This tool was created with the help of AI.

# third-party
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm

# Fonts
### Base-14 fonts are embedded in every PDF reader, need no font files, and
### survive PyInstaller bundling without any extra data files.
FONT_BODY = "Helvetica"
FONT_BOLD = "Helvetica-Bold"


class ColorPalette:
    """
    Report color tokens based on the supplied Merck color palette.
    These are the ReportLab equivalent of custom CSS properties.
    Change a value here and it affects every report.
    """

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


class Sizing:
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


class TextStyles:
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
            textColor=ColorPalette.BRAND,
        )

        self.subtitle = ParagraphStyle(
            name="ReportSubtitle",
            fontName=FONT_BODY,
            fontSize=10,
            leading=15,
            textColor=ColorPalette.MUTED,
        )

        self.metadata = ParagraphStyle(
            name="ReportMetadata",
            fontName=FONT_BODY,
            fontSize=9,
            leading=13,
            textColor=ColorPalette.MUTED,
        )

        self.heading = ParagraphStyle(
            name="SectionHeading",
            fontName=FONT_BOLD,
            fontSize=15,
            leading=19,
            textColor=ColorPalette.BRAND,
        )

        self.body = ParagraphStyle(
            name="Body",
            fontName=FONT_BODY,
            fontSize=10,
            leading=15,
            textColor=ColorPalette.INK,
        )

        self.note = ParagraphStyle(
            name="Note",
            fontName=FONT_BODY,
            fontSize=9,
            leading=14,
            textColor=ColorPalette.SLATE,
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
            textColor=ColorPalette.MUTED,
        )

        self.metric_value = ParagraphStyle(
            name="MetricValue",
            fontName=FONT_BOLD,
            fontSize=18,
            leading=21,
            textColor=ColorPalette.BRAND,
        )

        self.table_header = ParagraphStyle(
            name="TableHeader",
            fontName=FONT_BOLD,
            fontSize=9,
            leading=12,
            textColor=ColorPalette.WHITE,
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
            textColor=ColorPalette.INK,
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
            textColor=ColorPalette.SEVERITY_ERROR,
        )

        self.cell_warning = ParagraphStyle(
            name="TableCellWarning",
            parent=self.cell,
            fontName=FONT_BOLD,
            textColor=ColorPalette.SEVERITY_WARNING,
        )

        self.footer = ParagraphStyle(
            name="Footer",
            fontName=FONT_BODY,
            fontSize=9,
            leading=12,
            textColor=ColorPalette.MUTED,
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
