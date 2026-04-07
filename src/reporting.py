# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
#
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH

# stdlib
import logging
from queue import Queue
from datetime import datetime
from pathlib import Path

# third party
import ttkbootstrap as ttk
from ttkbootstrap.dialogs import Messagebox as modal

# local
from src.metadata import DATETIME_FORMAT

logger = logging.getLogger(__name__)


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
        verbose_printing: bool = True,
        populate_report: bool = True,
        populate_log: bool = True,
        use_timestamps: bool = True,
        use_msg_types: bool = True,
        timestamp: datetime | None = None,
    ) -> None:
        self.name = ""
        self.cleaned_name = ""
        self.report_name = ""
        self.file_path = Path()
        self.report_folder = Path()
        self.parent_window = parent_window
        self.output_dir = output_dir
        self.use_timestamps = use_timestamps
        self.use_msg_types = use_msg_types
        self.verbose = verbose_printing
        self.logging = populate_log
        self.report = populate_report
        self.width = 88

        if timestamp:
            self.timestamp = timestamp
        else:
            self.timestamp = datetime.now().strftime(DATETIME_FORMAT)

        self.report_lines = []
        self._modal_queue = Queue()
        self._modal_busy = False

    def _show_next_modal(self):
        """
        Processes the modal queue one at a time. FIFO.
        Each modal will schedule the next only after it is dismissed.
        """
        if self._modal_queue.empty():
            self._modal_busy = False
            return

        self._modal_busy = True

        # Unpacks stored tuple
        func, msg, title = self._modal_queue.get()

        def dismiss():
            self.parent_window.after(0, self._show_next_modal)

        def show_next():
            func(msg, title=title, parent=self.parent_window)
            dismiss()

        # Recursive call
        self.parent_window.after(0, show_next)

    def _queue_modal(self, func, msg: str, title: str) -> None:
        """
        Queue a modal dialog and start processing modals if not already busy.
        """
        if self.parent_window:
            self._modal_queue.put((func, msg, title))
            if not self._modal_busy:
                self.parent_window.after(0, self._show_next_modal)

    def _add_line(self, msg: str, msg_type: str | None = None) -> None:
        """
        Private function that adds a single string line to the report buffer.
        """
        if msg_type is None:
            msg_type = "UNKNOWN"

        timestamp = datetime.now().strftime(DATETIME_FORMAT)
        padding = f"{' ' * max(0, 9 - len(msg_type))}"

        line = f"{msg}"

        if self.use_msg_types:
            line = f"{padding}{msg_type}> " + line
        if self.use_timestamps:
            line = f"{timestamp}: " + line

        self.report_lines.append(line)

    def create_report(self, new_name: str, update_dirs: bool = True) -> None:
        """
        Name the report and by default initialize the directories.
        """
        self.report_lines = []

        self.name = new_name
        # NOTE: "my report"

        self.cleaned_name = self.name.replace(" ", "_")
        # NOTE: "my_report"

        self.report_name = f"{self.timestamp}_{self.cleaned_name}"
        # NOTE: "TIMESTAMP_my_report"

        self.report_folder = self.output_dir / self.report_name
        if update_dirs:
            self.report_folder.mkdir(parents=True, exist_ok=True)
        # NOTE: "BASE_DIR\TIMESTAMP_my_report"

        report_path = self.report_folder / self.cleaned_name
        # NOTE: "BASE_DIR\TIMESTAMP_my_report\my_report"

        self.file_path = report_path.with_suffix(".log")
        # NOTE: "BASE_DIR\TIMESTAMP_my_report\my_report.log"

    def debug(
        self,
        msg: str,
        report: bool | None = None,
        log: bool | None = None,
        verbose: bool | None = None,
        popup: bool = False,
    ) -> None:
        """
        Print, log and report debug information.
        """
        _log = self.logging if log is None else log
        _verbose = self.verbose if verbose is None else verbose
        _report = self.report if report is None else report

        if _log:
            logger.debug(msg)
        if _verbose:
            print(msg)
        if _report:
            self._add_line(msg, "DEBUG")
        if popup:
            self._queue_modal(modal.show_error, msg, "Debugger")

    def error(
        self,
        msg: str,
        report: bool | None = None,
        log: bool | None = None,
        verbose: bool | None = None,
        popup: bool = False,
    ) -> None:
        """
        Print, log and report lines with the error tag.
        """
        _log = self.logging if log is None else log
        _verbose = self.verbose if verbose is None else verbose
        _report = self.report if report is None else report

        if _log:
            logger.error(msg)
        if _verbose:
            print(msg)
        if _report:
            self._add_line(msg, "ERROR")
        if popup:
            self._queue_modal(modal.show_error, msg, "An error has occurred!")

    def exception(
        self,
        msg: str,
        report: bool | None = None,
        log: bool | None = None,
        verbose: bool | None = None,
        popup: bool = False,
    ) -> None:
        """
        Print, log and report exceptions. This will also display the exception path.
        By default uses instance defaults for report and log behavior.
        """
        _log = self.logging if log is None else log
        _verbose = self.verbose if verbose is None else verbose
        _report = self.report if report is None else report

        if _log:
            logger.exception(msg)
        if _verbose:
            print(msg)
        if _report:
            self._add_line(msg, "EXCEPTION")
        if popup:
            self._queue_modal(modal.show_error, msg, "An exception was thrown!")

    def info(
        self,
        msg: str,
        report: bool | None = None,
        log: bool | None = None,
        verbose: bool | None = None,
        popup: bool = False,
    ) -> None:
        """
        Print, log and report standard information.
        """
        _log = self.logging if log is None else log
        _verbose = self.verbose if verbose is None else verbose
        _report = self.report if report is None else report

        if _log:
            logger.info(msg)
        if _verbose:
            print(msg)
        if _report:
            self._add_line(msg, "INFO")
        if popup:
            self._queue_modal(modal.show_info, msg, "You should know...")

    def warning(
        self,
        msg: str,
        report: bool | None = None,
        log: bool | None = None,
        verbose: bool | None = None,
        popup: bool = False,
    ) -> None:
        """
        Print, log and report lines with the warning tag.
        """
        _log = self.logging if log is None else log
        _verbose = self.verbose if verbose is None else verbose
        _report = self.report if report is None else report

        if _log:
            logger.warning(msg)
        if _verbose:
            print(msg)
        if _report:
            self._add_line(msg, "WARNING")
        if popup:
            self._queue_modal(modal.show_warning, msg, "Warning!")

    def critical(
        self,
        msg: str,
        report: bool | None = None,
        log: bool | None = None,
        verbose: bool | None = None,
        popup: bool = False,
    ) -> None:
        """
        Print, log and report critical failures.
        """
        _log = self.logging if log is None else log
        _verbose = self.verbose if verbose is None else verbose
        _report = self.report if report is None else report

        if _log:
            logger.critical(msg)
        if _verbose:
            print(msg)
        if _report:
            self._add_line(msg, "CRITICAL")
        if popup:
            self._queue_modal(modal.show_error, msg, "CRITICAL FAILURE")

    def title(self, message: str) -> None:
        """
        Helper function to record a title.
        Uses a heavy square box.
        """
        inner_padding = self.width - 4
        padded = message.center(inner_padding)
        self.info(f"╔{'═' * (self.width - 2)}╗")
        self.info(f"║ { padded             } ║")
        self.info(f"╚{'═' * (self.width - 2)}╝")

    def subtitle(self, message: str) -> None:
        """
        Helper function to record a subtitle.
        Uses a light single-line box (less prominent than title).
        """
        inner_padding = self.width - 4
        padded = message.center(inner_padding)
        self.info(f"┌{'─' * (self.width - 2)}┐")
        self.info(f"│ { padded             } │")
        self.info(f"└{'─' * (self.width - 2)}┘")

    def simple_title(self, message: str) -> None:
        """
        Helper function to record a simple highlighted title.
        Uses a simple line format.
        """
        inner_padding = self.width - 2
        padding = (inner_padding - len(message)) // 2
        remainder = (inner_padding - len(message)) % 2
        self.info(f"{'─'*padding} {message} {'─'*(padding + remainder)}")

    def highlight_error(self, message: str, is_critical: bool = False) -> None:
        """
        Helper function to highlight an error within the process.
        Uses a double-line box to stand out.
        """
        # OLD
        # func = self.critical if is_critical else self.error
        # inner_padding = self.width - 4
        # padded = message.center(inner_padding)
        # func(f"X{'═' * (self.width - 2)}X")
        # func(f"║ { padded             } ║")
        # func(f"X{'═' * (self.width - 2)}X")

        # TEST:
        func = self.critical if is_critical else self.error

        inner = self.width - 2
        label = f" {message} "
        if len(label) > inner:
            label = label[: max(0, inner - 1)] + "..."

        pad_total = inner - len(label)
        left = pad_total // 2
        right = pad_total - left

        line = "X" + ("=" * left) + label + ("=" * right) + "X"

        func(line)

    def highlight_titled_error(
        self, message: str, title: str = "COMPARISON FAILED", is_critical: bool = False
    ) -> None:
        """
        Helper function to highlight an error and a title.
        Uses a heavy double-line box, with a separator between title and message.
        """
        func = self.critical if is_critical else self.error
        inner_padding = self.width - 4
        t = title.upper().center(inner_padding)
        m = message.center(inner_padding)

        func(f"X{'═' * (self.width - 2)}X")
        func(f"║ {t                   } ║")
        func(f"╠{'═' * (self.width - 2)}╣")
        func(f"║ {m                   } ║")
        func(f"X{'═' * (self.width - 2)}X")

    def divider(self) -> None:
        """
        A full-width heavy divider. Used between major sections.
        """
        self.info("═" * self.width)

    def separator(self) -> None:
        """
        A full-width light divider. Used between minor sections.
        """
        self.info("─" * self.width)

    def section(self) -> None:
        """
        A half-width light divider. Used between minor sections.
        """
        self.info("─" * (self.width // 2))

    def error_divider(self) -> None:
        """
        A full-width light divider. Used between minor sections.
        """
        self.error("=" * self.width)

    def error_separator(self) -> None:
        """
        A full-width light divider. Used between minor sections.
        """
        self.error("-" * self.width)

    def error_section(self) -> None:
        """
        A half-width light divider. Used between minor sections.
        """
        self.error("─" * (self.width // 2))

    def save_report(self, popup: bool = False) -> None:
        """
        Saves the report to a file.
        """
        if not self.file_path.name:
            raise RuntimeError("create_report() must be called before save_report().")
        try:
            notice = f"{self.name} report saved to:\n{self.file_path}\n"
            if popup:
                self._queue_modal(modal.show_info, notice, "Saving...")
            self._add_line(notice, "INFO")
            with open(self.file_path, "w", encoding="utf-8") as file:
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
    test.info("Only shown in logging, not reporting", log=False)
    test.info("Showing popup!", popup=True)
    test.debug("Debugging")
    test.error("Error")
    test.exception("Exception!")
    test.save_report()

    window.mainloop()
