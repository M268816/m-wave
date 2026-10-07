# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH
# This tool was created with the help of AI.


from dataclasses import dataclass, field

from reportlab.platypus import Flowable, Spacer

from m_wave.core.pdf_reporting import (
    Metrics,
    PDFReportData,
    ReportStyles,
    data_table,
    metric_grid,
    section_heading,
    status_banner,
    thousands,
)


@dataclass
class ExampleReportData(PDFReportData):
    example_int: int = 0
    example_str: str = "Hello Example"
    example_list: list[str] = field(default_factory=list)

    def build_elements(
        self,
        styles: ReportStyles,
        width: float,
    ) -> list[Flowable]:
        elements: list[Flowable] = [
            status_banner(styles, self.status, self.status_message, width),
            Spacer(1, Metrics.GAP_SECTION),
            section_heading(styles, "Summary"),
            Spacer(1, Metrics.GAP_SECTION),
            metric_grid(
                styles,
                [
                    ("Example number", thousands(self.example_int)),
                    ("Example text", self.example_str),
                ],
                width,
                columns=2,
            ),
            Spacer(1, Metrics.GAP_SECTION),
            section_heading(styles, "Example list"),
            Spacer(1, 10),
            data_table(
                styles,
                headers=["Item"],
                rows=[[item] for item in self.example_list],
                width=width,
            ),
        ]

        return elements
