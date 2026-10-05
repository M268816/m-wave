# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH
# This tool was created with the help of AI.

# stdlib
from datetime import UTC, datetime

# third party
from pathlib import Path

# local
from m_wave.core.pdf_reporting import PDFReportStatus
from m_wave.core.reporting import Reporting
from m_wave.core.utils import DATETIME_FORMAT_MERCK, USER
from m_wave.wave_packs.example.pdf_reporting import ExampleReportData


class ExampleProcess:
    def __init__(self, report: Reporting, file_path_1: Path) -> None:
        self.report = report
        self.file_path_1 = file_path_1

    def run(self) -> None:
        self.report.title("This is an example WavePack")
        merck_time = datetime.now(UTC).strftime(DATETIME_FORMAT_MERCK)
        self.report.subtitle(f"Started by: {USER} on {merck_time}")

        self.report.simple_title(
            "Phases are a good way to display process progression."
        )

        self.report.info("Outputting Info for your user is critical for UX.")

        self.report.divider()

        self.report.info("Here is that file you requested!")
        self.report.info(f"File Path: {self.file_path_1}")

        self.report.info("Now to make you a fancy PDF!")

        report_data = ExampleReportData(
            "Example Report",
            "Example ID 01-1",
            "M268816",
            datetime.now(UTC),
            PDFReportStatus.PASS,
            "Just a little subtitle",
            {"no": Path()},
            100,
            "Hello new Example",
            ["this", "is", "a", "example", "list"],
        )

        self.report.create_pdf_report(report_data)

        self.report.simple_title("Make sure to save the report!")

        self.report.divider()

        self.report.critical("Saving!")

        self.report.save_report()
