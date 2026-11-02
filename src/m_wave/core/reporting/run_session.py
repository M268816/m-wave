# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH
# This tool was created with the help of AI.

"""
One process run: its name, ID, folder, technical run log and PDF summary.

    with RunSession.start(PATHS.reports_dir, "Example Report") as session:
        session.log.title("Example")                 # -> run.log, GUI, dev log
        template = ExamplePDFReportTemplate(
            title="Example Report",
            report_id=session.report_id,
            user=session.user,
            created_date=session.started_at,
            status=PDFReportStatus.PASS,
        )
        session.render_pdf(template)                 # -> summary.pdf

Folder layout:
    reports/(<timestamp>)_<name>/
        run.log          technical run log, written as the run goes
        summary.pdf      non-technical summary
        <artifacts>      use session.path_for("file.csv") until ArtifactStore lands

On exit the session always closes run.log, even if the run raised. If a
``failure_template`` factory is given, an ERRORED PDF is rendered when the run
raised before a PDF was produced.
"""

from __future__ import annotations

# stdlib
import logging
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from types import TracebackType
from typing import TYPE_CHECKING

# local
from m_wave.core.context import USER
from m_wave.core.paths import PATHS
from m_wave.core.reporting.log_setup import set_active_run_id
from m_wave.core.reporting.pdf_builder import PDFReportBuilder, PDFReportTemplate
from m_wave.core.reporting.run_log import LABEL_ATTR, RunLog
from m_wave.core.utils import DATETIME_FORMAT, DATETIME_FORMAT_MERCK

if TYPE_CHECKING:
    from typing import Self

logger = logging.getLogger(__name__)

RUN_LOG_FILENAME = "run.log"
PDF_FILENAME = "summary.pdf"

FailureTemplateFactory = Callable[["RunSession", BaseException], PDFReportTemplate]


def clean_name(name: str) -> str:
    """'my report*name ' -> 'my_report_name'"""
    return name.strip().replace(" ", "_").replace("*", "") or "Not_Named"


class RunSession:
    """Owns everything that belongs to a single process run."""

    def __init__(
        self,
        output_dir: Path,
        name: str,
        log: RunLog | None = None,
        user: str = USER,
        started_at: datetime | None = None,
        failure_template: FailureTemplateFactory | None = None,
    ) -> None:
        self.name = name.strip() or "Not Named"
        self.cleaned_name = clean_name(name)
        self.user = user
        self.started_at = (started_at or datetime.now()).astimezone()
        self.timestamp = self.started_at.strftime(DATETIME_FORMAT)

        self.folder_name = f"({self.timestamp})_{self.cleaned_name}"
        self.run_dir = output_dir / self.folder_name
        self.log_path = self.run_dir / RUN_LOG_FILENAME
        self.pdf_path: Path | None = None

        self.log = log or RunLog()
        self.failure_template = failure_template

        self._file_handler: logging.Handler | None = None
        self._perf_start = 0.0
        self._open = False

    # -- identity -----------------------------------------------------------
    @property
    def report_id(self) -> str:
        """Shown on the PDF and tagged on every developer-log line of this run."""
        return self.folder_name

    # -- lifecycle ----------------------------------------------------------
    @classmethod
    def start(
        cls,
        output_dir: Path,
        name: str,
        log: RunLog | None = None,
        failure_template: FailureTemplateFactory | None = None,
    ) -> RunSession:
        session = cls(output_dir, name, log=log, failure_template=failure_template)
        session.open()
        return session

    def open(self) -> None:
        if self._open:
            return
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self._file_handler = self.log.attach_file(self.log_path)
        set_active_run_id(self.report_id)
        self._perf_start = time.perf_counter()
        self._open = True

        logger.debug("Run session opened: %s", self.run_dir)
        self.log.info(f"Run:        {self.name}")
        self.log.info(f"Run ID:     {self.report_id}")
        self.log.info(f"User:       {self.user}")
        self.log.info(f"Started:    {self.started_at.strftime(DATETIME_FORMAT_MERCK)}")
        self.log.info(f"Run folder: {self.run_dir}")
        self.log.separator()

    def close(self) -> None:
        if not self._open:
            return
        elapsed = time.perf_counter() - self._perf_start
        self.log.separator()
        self.log.info(f"Run finished in {elapsed:.2f}s. Run log: {self.log_path.name}")
        if self.pdf_path is None:
            self.log.warning("No PDF summary was produced for this run.")
        self.log.detach(self._file_handler)
        self._file_handler = None
        logger.debug("Run session closed: %s", self.run_dir)
        set_active_run_id(None)
        self._open = False

    def __enter__(self) -> Self:
        self.open()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        try:
            if exc is not None:
                self.log.logger.error(
                    f"Run aborted: {exc}",
                    exc_info=(exc_type, exc, tb),
                    extra={LABEL_ATTR: "EXCEPTION"},
                )
                if self.pdf_path is None and self.failure_template is not None:
                    try:
                        self.render_pdf(self.failure_template(self, exc))
                    except Exception:
                        logger.exception("Could not build the failure PDF template.")
        finally:
            self.close()
        # Do not swallow the exception; the controller decides what the user sees.

    # -- outputs ------------------------------------------------------------
    def path_for(self, filename: str) -> Path:
        """Path inside the run folder, for CSV and other artifacts."""
        return self.run_dir / filename

    def render_pdf(
        self,
        template: PDFReportTemplate,
        filename: str = PDF_FILENAME,
        page_size: tuple[float, float] | None = None,
        logo_path: Path | None = None,
    ) -> Path | None:
        """
        Render ``template`` into the run folder.

        Returns the PDF path, or None on failure. A failure is written to the run
        log (short) and the developer log (with traceback); it never raises, so a
        broken PDF cannot hide the rest of the run's results.
        """
        output_path = self.run_dir / filename
        try:
            builder = PDFReportBuilder(
                page_size=page_size, logo_path=logo_path or PATHS.logo_path
            )
            builder.build(template, output_path)
        except Exception:
            self.log.exception("Unable to create the PDF summary.")
            return None
        self.pdf_path = output_path
        self.log.info(
            f"PDF summary saved: {output_path.name} ({template.status.label})"
        )
        return output_path
