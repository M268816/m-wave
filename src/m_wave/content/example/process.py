# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH
# This tool was created with the help of AI.

"""
Example WavePack process. This is the reference pattern for the four outputs:

    self.log      -> technical run log (run.log + GUI + developer log)
    logger        -> developer log only (your debugging detail)
    template      -> PDF summary for non-technical reviewers
    self.notifier -> pop-ups / questions for the operator
"""

# stdlib
import logging
from pathlib import Path

# local
from m_wave.content.example.pdf_template import ExamplePDFReportTemplate
from m_wave.core.reporting.notifier import Notifier
from m_wave.core.reporting.pdf_utils import PDFReportStatus
from m_wave.core.reporting.run_session import RunSession

logger = logging.getLogger(__name__)


class ExampleProcess:
    def __init__(
        self, session: RunSession, notifier: Notifier, file_path_1: Path
    ) -> None:
        self.session = session
        self.log = session.log
        self.notifier = notifier
        self.file_path_1 = file_path_1

    def run(self) -> PDFReportStatus:
        self.log.title("This is an example WavePack")

        # NOTE: PHASE 1, technical steps go to the run log.
        self.log.simple_title("Phases are a good way to display process progression.")
        self.log.info("Outputting info for your user is critical for UX.")
        self.log.info(f"File Path: {self.file_path_1}")

        # Developer-only detail: never shown to reviewers.
        logger.debug(
            "Input resolved to %r (exists=%s)",
            self.file_path_1.resolve(),
            self.file_path_1.exists(),
        )

        # NOTE: PHASE 2, decide the outcome once, here.
        status = (
            PDFReportStatus.PASS if self.file_path_1.exists() else PDFReportStatus.FAIL
        )
        if status is PDFReportStatus.FAIL:
            self.log.highlight_error("INPUT FILE NOT FOUND")

        # NOTE: REPORT PHASE, the PDF is built from data, never from log lines.
        self.log.simple_title("Building the PDF summary.")
        template = ExamplePDFReportTemplate(
            title="Example Report",
            report_id=self.session.report_id,
            user=self.session.user,
            created_date=self.session.started_at,
            status=status,
            subtitle="Just a little subtitle",
            example_int=100,
            example_str="Hello new Example",
            example_list=["this", "is", "a", "example", "list"],
        )
        self.session.render_pdf(template)

        # No save_report(): run.log is written as the run goes and closed by the
        # session when the `with` block ends.
        return status
