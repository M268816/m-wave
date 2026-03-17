# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
#
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH

# stdlib
import logging
from datetime import datetime
from pathlib import Path

# third party
import ttkbootstrap as ttk
from ttkbootstrap.dialogs import Messagebox as modal

logger = logging.getLogger(__name__)

DATETIME_FORMAT = "%Y_%m_%dT%H-%M-%S"  # add %f for ms


class Reporting:
    """
    A class that creates a report for a single process run by the app. It appends
    lines of strings to a list and writes them to a text file. Lines will also
    be added to the log file associated with the main logger.
    """

    def __init__(
        self,
        parent_window: ttk.Window,
        output_dir: Path,
        use_timestamps: bool = False,
        timestamp: datetime | None = None,
    ) -> None:
        self.name = None
        self.file_name = None
        self.report_name = None
        self.parent_window = parent_window
        self.output_dir = output_dir
        self.use_timestamps = use_timestamps

        if timestamp:
            self.timestamp = timestamp
        else:
            self.timestamp = datetime.now().strftime(DATETIME_FORMAT)

        self.report_lines = []

    def _add_line(self, msg: str, msg_type: str | None = None) -> None:
        """
        Private function that adds a single string line to the report buffer.
        """
        if msg_type is None:
            msg_type = "INFO"

        timestamp = datetime.now().strftime(DATETIME_FORMAT)
        ts_line = f"{timestamp}:{msg_type}::{msg}"
        line = f"{msg_type}::{msg}"

        if self.use_timestamps:
            self.report_lines.append(ts_line)
        else:
            self.report_lines.append(line)

    def create_report(self, new_name: str, update_dirs: bool = True) -> None:
        """
        Name the report and by default initialize the directories.
        """
        self.name = new_name
        # NOTE: "my report"
        self.cleaned_name = self.name.replace(" ", "_")
        # "my_report"
        self.report_name = f"{self.timestamp}_{self.cleaned_name}"
        # NOTE: "13_01_2026T11-58-48_my_report"

        self.report_folder = self.output_dir / self.cleaned_name
        if update_dirs:
            self.report_folder.mkdir(parents=True, exist_ok=True)
            # NOTE: "BASE_DIR\my_report"

        report_path = self.report_folder / self.report_name
        # NOTE: "BASE_DIR\my_report\13_01_2026T11-58-48_my_report"

        self.file_name = report_path.with_suffix(".log")
        # NOTE: "BASE_DIR\my_report\13_01_2026T11-58-48_my_report.log"

    def debug(self, msg: str, log_only: bool = True, popup: bool = False) -> None:
        """
        Print, log and report debug information. Only posts to log by default.
        """
        print(msg)
        logger.debug(msg)
        if popup and self.parent_window:
            self.parent_window.after(
                0,
                lambda m=msg: modal.show_warning(
                    m, title="DEBUG", parent=self.parent_window
                ),
            )
        if not log_only:
            self._add_line(msg, "DEBUG")

    def error(self, msg: str, log_only: bool = False, popup: bool = False) -> None:
        """
        Print, log and report lines with the error tag.
        """
        print(msg)
        logger.error(msg)
        if popup and self.parent_window:
            self.parent_window.after(
                0,
                lambda m=msg: modal.show_error(
                    m, title="ERROR", parent=self.parent_window
                ),
            )
        if not log_only:
            self._add_line(msg, "ERROR")

    def exception(self, msg: str, log_only: bool = True, popup: bool = False) -> None:
        """
        Print, log and report exceptions. This will also display the exception path.
        By default it will only append to the logging file.
        """
        print(msg)
        logger.exception(msg)
        if popup and self.parent_window:
            self.parent_window.after(
                0,
                lambda m=msg: modal.show_error(
                    m, title="An exception was thrown!", parent=self.parent_window
                ),
            )
        if not log_only:
            self._add_line(msg, "EXCEPTION")

    def info(self, msg: str, log_only: bool = False, popup: bool = False) -> None:
        """
        Print, log and report standard information.
        """
        print(msg)
        logger.info(msg)
        if popup and self.parent_window:
            self.parent_window.after(
                0,
                lambda m=msg: modal.show_info(
                    m, title="You should know...", parent=self.parent_window
                ),
            )
        if not log_only:
            self._add_line(msg, "INFO")

    def warning(self, msg: str, log_only: bool = False, popup: bool = False) -> None:
        """
        Print, log and report lines with the warning tag.
        """
        print(msg)
        logger.warning(msg)
        if popup and self.parent_window:
            self.parent_window.after(
                0,
                lambda m=msg: modal.show_warning(
                    m, title="Warning!", parent=self.parent_window
                ),
            )
        if not log_only:
            self._add_line(msg, "WARNING")

    def critical(self, msg: str, log_only: bool = False, popup: bool = True) -> None:
        """
        Print, log and report critical failures.
        """
        print(msg)
        logger.critical(msg)
        if popup and self.parent_window:
            self.parent_window.after(
                0,
                lambda m=msg: modal.show_error(
                    m, title="CRITICAL FAILURE!", parent=self.parent_window
                ),
            )
        if not log_only:
            self._add_line(msg, "CRITICAL")

    def title(self, message: str) -> None:
        """
        Helper function to record a title.
        """
        self.info(f"{'='*80}")
        self.info(message)
        self.info(f"{'='*80}")

    def subtitle(self, message: str) -> None:
        """
        Helper function to record a subtitle.
        """
        self.info(f"{'-'*60}")
        self.info(message)
        self.info(f"{'-'*60}")

    def highlight_error(self, message: str, is_critical: bool = False) -> None:
        """
        Helper function to highlight an error within the process.
        """
        func = self.critical if is_critical else self.error
        func(f"!{'~'*58}!")
        func(message)
        func(f"!{'~'*58}!")

    def highlight_titled_error(
        self, message: str, title: str = "COMPARISON FAILED", is_critical: bool = False
    ) -> None:
        """
        Helper function to highlight an error and a title
        """
        func = self.critical if is_critical else self.error
        func(f"{'!'*80}")
        func(title.upper())
        func(message)
        func(f"{'!'*80}")

    def save_report(self, popup: bool = False) -> None:
        """
        Saves the report to a file.
        """
        if self.file_name is None:
            raise RuntimeError("create_report() must be called before save_report().")
        try:
            notice = f"{self.name} report saved to: {self.report_name}"
            if popup and self.parent_window:
                self.parent_window.after(
                    0,
                    lambda m=notice: modal.show_info(
                        m, title="Saving...", parent=self.parent_window
                    ),
                )
            self._add_line(notice, "INFO")
            with open(self.file_name, "w", encoding="utf-8") as file:
                file.write("\n".join(self.report_lines))
            print(notice)
            logger.info(notice)
        except Exception as e:
            error_msg = f"Error saving report:\n{e}"
            self.exception(error_msg, popup=True)


if __name__ == "__main__":
    from src.paths import REPORTS_DIR

    window = ttk.Window(themename="superhero")

    test = Reporting(window, output_dir=REPORTS_DIR)
    test.create_report("reporting_test")
    test.info("Saving to test_reporting dir.")
    test.info("Only shown in logging, not reporting", log_only=True)
    test.info("Showing popup!", popup=True)
    test.debug("Debugging")
    test.error("Error")
    test.exception("Exception!")
    test.save_report()

    window.mainloop()
