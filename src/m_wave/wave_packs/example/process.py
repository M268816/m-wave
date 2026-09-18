# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH
# This tool was created with the help of AI.

# stdlib
from datetime import datetime

# third party
from pathlib import Path

# local
from m_wave.core.reporting import Reporting
from m_wave.core.utils import DATETIME_FORMAT_MERCK, USER


class ExampleProcess:
    def __init__(self, report: Reporting, file_path_1: Path) -> None:
        self.report = report
        self.file_path_1 = file_path_1

    def run(self) -> None:
        self.report.title("This is an example WavePack")
        merck_time = datetime.now().strftime(DATETIME_FORMAT_MERCK)
        self.report.subtitle(f"Started by: {USER} on {merck_time}")

        self.report.simple_title(
            "Phases are a good way to display process progression."
        )

        self.report.info("Outputting Info for your user is critical for UX.")

        self.report.divider()

        self.report.info("Here is that file you requested!")
        self.report.info(f"File Path: {self.file_path_1}")

        self.report.simple_title("Make sure to save the report!")

        self.report.divider()

        self.report.critical("Saving!")

        self.report.save_report()
