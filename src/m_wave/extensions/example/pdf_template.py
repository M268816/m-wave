# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH
# This tool was created with the help of AI.


# stdlib
from dataclasses import dataclass, field

# third-party
from reportlab.platypus import Flowable, Spacer

# local
from m_wave.core.reporting.pdf_builder import PDFReportTemplate
from m_wave.core.reporting.pdf_components import (
    data_metric_grid,
    data_table,
    section_heading,
    status_banner,
)
from m_wave.core.reporting.pdf_styles import Sizing, TextStyles
from m_wave.core.reporting.pdf_utils import thousands


@dataclass
class ExamplePDFReportTemplate(PDFReportTemplate):
    """
    This extends the base PDFReportTemplate class.

    The example attributes below are passed through while building the widget elements.

    You must create your own build_components() function for a report to display custom
    content and data.
    """

    # custom attributes for your reporting needs
    example_int: int = 0
    example_str: str = "Hello Example"
    example_list: list[str] = field(default_factory=list)

    def build_components(
        self,
        text_styles: TextStyles,
        width: float,
    ) -> list[Flowable]:
        elements: list[Flowable] = [
            status_banner(text_styles, self.status, self.status_message, width),
            Spacer(1, Sizing.GAP_SECTION),
            section_heading(text_styles, "Summary"),
            Spacer(1, Sizing.GAP_SECTION),
            data_metric_grid(
                text_styles,
                [
                    ("Example number", thousands(self.example_int)),
                    ("Example text", self.example_str),
                ],
                width,
                columns=2,
            ),
            Spacer(1, Sizing.GAP_SECTION),
            section_heading(text_styles, "Example list"),
            Spacer(1, 10),
            data_table(
                text_styles,
                headers=["Item"],
                rows=[[item] for item in self.example_list],
                width=width,
            ),
        ]

        return elements
