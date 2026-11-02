# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH
# This tool was created with the help of AI.

# stdlib
from collections.abc import Sequence
from pathlib import Path

# third-party
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Flowable,
    HRFlowable,
    Image,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

# local
from m_wave.core.reporting.pdf_styles import ColorPalette, Sizing, TextStyles
from m_wave.core.reporting.pdf_utils import PDFReportStatus

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
    bar_width = Sizing.BAR_WIDTH

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
    text_styles: TextStyles,
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
    block: list[Flowable] = [Paragraph(title, text_styles.title)]

    if subtitle:
        block.append(Spacer(1, 5))
        block.append(Paragraph(subtitle, text_styles.subtitle))

    if metadata:
        block.append(Spacer(1, 15))
        for label, value in metadata:
            block.append(Paragraph(f"{label}: {value}", text_styles.metadata))

    if logo_path is not None and logo_path.exists():
        logo = _scaled_image(logo_path, target_width=32 * mm)
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
            thickness=Sizing.ACCENT_RULE,
            color=ColorPalette.ACCENT,
            spaceBefore=0,
            spaceAfter=0,
        )
    )
    elements.append(Spacer(1, 22))

    return elements


def status_banner(
    text_styles: TextStyles,
    status: PDFReportStatus,
    message: str,
    width: float,
) -> Flowable:
    """
    The PASS / FAIL / WARNING panel.
    """
    label_style = ParagraphStyle(
        name=f"StatusLabel-{status.value}",
        parent=text_styles.status_label,
        textColor=status.text,
    )
    body_style = ParagraphStyle(
        name=f"StatusBody-{status.value}",
        parent=text_styles.status_body,
        textColor=status.text,
    )

    content = [
        Paragraph(status.label, label_style),
        Spacer(1, 3),
        Paragraph(message, body_style),
    ]

    return _bar_panel(content, width, status.fill, status.edge)


def data_metric_grid(
    text_styles: TextStyles,
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
                [Paragraph(label.upper(), text_styles.metric_label)],
                [Paragraph(value, text_styles.metric_value)],
            ],
            colWidths=[card_width],
        )
        inner.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), ColorPalette.PANEL),
                    (
                        "LINEABOVE",
                        (0, 0),
                        (-1, 0),
                        Sizing.METRIC_RULE,
                        ColorPalette.ACCENT,
                    ),
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


def section_heading(text_styles: TextStyles, text: str) -> Flowable:
    """A section heading with the hairline rule beneath it."""
    heading = Table(
        [[Paragraph(text, text_styles.heading)]],
    )
    heading.setStyle(
        TableStyle(
            [
                ("LINEBELOW", (0, 0), (-1, -1), 2, ColorPalette.RULE),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return heading


def data_table(
    text_styles: TextStyles,
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
            text_styles.table_header_right
            if index in right_aligned
            else text_styles.table_header,
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
                style = (
                    text_styles.cell_number
                    if index in right_aligned
                    else text_styles.cell
                )
                cells.append(Paragraph(str(value), style))
        body_rows.append(cells)

    table = Table(
        [header_cells, *body_rows],
        colWidths=col_widths,
        repeatRows=1,
    )

    commands = [
        ("BACKGROUND", (0, 0), (-1, 0), ColorPalette.BRAND),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), Sizing.CELL_PAD_X),
        ("RIGHTPADDING", (0, 0), (-1, -1), Sizing.CELL_PAD_X),
        ("TOPPADDING", (0, 0), (-1, -1), Sizing.CELL_PAD_Y),
        ("BOTTOMPADDING", (0, 0), (-1, -1), Sizing.CELL_PAD_Y),
        ("LINEBELOW", (0, 0), (-1, -1), 1, ColorPalette.RULE),
    ]

    # Zebra striping. Row 0 is the header, so the first body row is row 1 and
    # the "even" rows of the original CSS are the odd ReportLab row indexes.
    for offset in range(len(body_rows)):
        if offset % 2 == 1:
            row_index = offset + 1
            commands.append(
                ("BACKGROUND", (0, row_index), (-1, row_index), ColorPalette.ZEBRA)
            )

    table.setStyle(TableStyle(commands))
    return table


def note_box(text_styles: TextStyles, text: str, width: float) -> Flowable:
    """A muted advisory panel, used for caveats and pointers to other files."""
    return _bar_panel(
        [Paragraph(text, text_styles.note)],
        width,
        ColorPalette.PANEL,
        ColorPalette.NOTE_EDGE,
    )


def empty_state(text_styles: TextStyles, text: str) -> Flowable:
    """
    The message shown where a table would be if there were no rows.
    """
    return Paragraph(text, text_styles.body)


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
    return _scaled_image(path, target_width=width)
