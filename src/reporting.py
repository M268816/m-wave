# stdlib
import logging
from datetime import datetime
from pathlib import Path

# third party
import ttkbootstrap as ttk
from ttkbootstrap.dialogs import Messagebox as modal

# local
from src.paths import BASE_DIR

logger = logging.getLogger(__name__)

DATETIME_FORMAT = "%Y-%m-%dT%H_%M_%S-%f"


class Reporting:
    """
    A class that creates a report for a single process run by the app. It appends
    lines of strings to a list and writes them to a text file. Lines will also
    be added to the log file associated with the main logger.
    """

    def __init__(
        self,
        name: str,
        parent_window: ttk.Window,
        use_timestamps: bool = True,
        timestamp: str | None = None,
        output_dir: Path | None = None,
    ) -> None:
        if timestamp is None:
            timestamp = datetime.now().strftime(DATETIME_FORMAT)
        if output_dir is None:
            output_dir = BASE_DIR
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        self.use_timestamps = use_timestamps
        self.parent = parent_window
        self.name = name
        self.report_name = f"{timestamp}_{name.replace(' ', '_')}"
        self.report_path = output_dir / self.report_name
        self.file_name = self.report_path.with_suffix(".log")
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

    def debug(self, msg: str, log_only: bool = True, popup: bool = False) -> None:
        """
        Print, log and report debug information. Only posts to log by default.
        """
        print(msg)
        logger.debug(msg)
        if popup and self.parent:
            self.parent.after(
                0,
                lambda m=msg: modal.show_warning(m, title="DEBUG", parent=self.parent),
            )
        if not log_only:
            self._add_line(msg, "DEBUG")

    def error(self, msg: str, log_only: bool = False, popup: bool = False) -> None:
        """
        Print, log and report lines with the error tag.
        """
        print(msg)
        logger.error(msg)
        if popup and self.parent:
            self.parent.after(
                0,
                lambda m=msg: modal.show_error(m, title="ERROR", parent=self.parent),
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
        if popup and self.parent:
            self.parent.after(
                0,
                lambda m=msg: modal.show_error(
                    m, title="An exception was thrown!", parent=self.parent
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
        if popup and self.parent:
            self.parent.after(
                0,
                lambda m=msg: modal.show_info(
                    m, title="You should know...", parent=self.parent
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
        if popup and self.parent:
            self.parent.after(
                0,
                lambda m=msg: modal.show_warning(
                    m, title="Warning!", parent=self.parent
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
        if popup and self.parent:
            self.parent.after(
                0,
                lambda m=msg: modal.show_error(
                    m, title="CRITICAL FAILURE!", parent=self.parent
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

    def save(self, popup: bool = False) -> None:
        """
        Saves the report to a file.
        """
        try:
            notice = f"{self.name} report saved to: {self.report_path}"
            if popup and self.parent:
                self.parent.after(
                    0,
                    lambda m=notice: modal.show_info(
                        m, title="Saving...", parent=self.parent
                    ),
                )
            self._add_line(notice, "INFO")
            with open(self.file_name, "w", encoding="utf-8") as file:
                file.write("\n".join(self.report_lines))
            print(notice)
            logger.info(notice)
        except Exception as e:
            error_msg = f"Error saving report:\n{e}"
            print(error_msg)
            logger.exception(error_msg)


if __name__ == "__main__":
    from src.paths import REPORTS_DIR

    window = ttk.Window(themename="superhero")

    test = Reporting("reporting_test", window, output_dir=REPORTS_DIR)
    test.info("Saving to test_reporting dir.")
    test.info("Only shown in logging, not reporting", log_only=True)
    test.info("Showing popup!", popup=True)
    test.debug("Debugging")
    test.error("Error")
    test.exception("Exception!")
    test.save()

    window.mainloop()
