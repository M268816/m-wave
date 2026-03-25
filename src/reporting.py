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
from src.paths import ASSET_DIR

logger = logging.getLogger(__name__)
LOGO_PATH = ASSET_DIR / "logo.png"


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
        self.name = ""
        self.cleaned_name = ""
        self.report_name = ""
        self.file_path = Path()
        self.report_folder = Path()
        self.parent_window = parent_window
        self.parent_window.iconphoto(False, LOGO_PATH)
        self.output_dir = output_dir
        self.use_timestamps = use_timestamps

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
        ts_line = f"{timestamp}:{' '*abs(7-len(msg_type))}{msg_type}> {msg}"
        line = f"{' '*abs(7-len(msg_type))}{msg_type}> {msg}"

        if self.use_timestamps:
            self.report_lines.append(ts_line)
        else:
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

    def debug(self, msg: str, log_only: bool = True, popup: bool = False) -> None:
        """
        Print, log and report debug information. Only posts to log by default.
        """
        print(msg)
        logger.debug(msg)
        if popup:
            self._queue_modal(modal.show_error, msg, "Debugger")
        if not log_only:
            self._add_line(msg, "DEBUG")

    def error(self, msg: str, log_only: bool = False, popup: bool = False) -> None:
        """
        Print, log and report lines with the error tag.
        """
        print(msg)
        logger.error(msg)
        if popup:
            self._queue_modal(modal.show_error, msg, "An error has occurred!")
        if not log_only:
            self._add_line(msg, "ERROR")

    def exception(self, msg: str, log_only: bool = True, popup: bool = False) -> None:
        """
        Print, log and report exceptions. This will also display the exception path.
        By default it will only append to the logging file.
        """
        print(msg)
        logger.exception(msg)
        if popup:
            self._queue_modal(modal.show_error, msg, "An exception was thrown!")
        if not log_only:
            self._add_line(msg, "EXCEPTION")

    def info(self, msg: str, log_only: bool = False, popup: bool = False) -> None:
        """
        Print, log and report standard information.
        """
        print(msg)
        logger.info(msg)
        if popup:
            self._queue_modal(modal.show_info, msg, "You should know...")
        if not log_only:
            self._add_line(msg, "INFO")

    def warning(self, msg: str, log_only: bool = False, popup: bool = False) -> None:
        """
        Print, log and report lines with the warning tag.
        """
        print(msg)
        logger.warning(msg)
        if popup:
            self._queue_modal(modal.show_warning, msg, "Warning!")
        if not log_only:
            self._add_line(msg, "WARNING")

    def critical(self, msg: str, log_only: bool = False, popup: bool = True) -> None:
        """
        Print, log and report critical failures.
        """
        print(msg)
        logger.critical(msg)
        if popup:
            self._queue_modal(modal.show_error, msg, "CRITICAL FAILURE")
        if not log_only:
            self._add_line(msg, "CRITICAL")

    def title(self, message: str) -> None:
        """
        Helper function to record a title.
        Uses a heavy square box.
        """
        m_len = len(message)
        self.info(f"╔═{'═'*m_len}═╗")
        self.info(f"║ { message } ║")
        self.info(f"╚═{'═'*m_len}═╝")

    def subtitle(self, message: str) -> None:
        """
        Helper function to record a subtitle.
        Uses a light single-line box (less prominent than title).
        """
        m_len = len(message)
        self.info(f"┌─{'─'*m_len}─┐")
        self.info(f"│ { message } │")
        self.info(f"└─{'─'*m_len}─┘")

    def simple_title(self, message: str, width: int = 88) -> None:
        """
        Helper function to record a simple highlighted title.
        Uses a simple line format.
        """
        m_len = len(message)
        s_len = (width - m_len) // 2
        if m_len >= width:
            self.info(f"─{message}─")
        else:
            self.info(f"{'─'*s_len} {message} {'─'*s_len}")

    def highlight_error(self, message: str, is_critical: bool = False) -> None:
        """
        Helper function to highlight an error within the process.
        Uses a double-line box to stand out.
        """
        func = self.critical if is_critical else self.error
        m_len = len(message)
        func(f"X═{'═'*m_len}═X")
        func(f"║ { message } ║")
        func(f"X═{'═'*m_len}═X")

    def highlight_titled_error(
        self, message: str, title: str = "COMPARISON FAILED", is_critical: bool = False
    ) -> None:
        """
        Helper function to highlight an error and a title.
        Uses a heavy double-line box, with a separator between title and message.
        """
        func = self.critical if is_critical else self.error

        t = title.upper()
        w = max(len(t), len(message))  # inner text width (excluding the spaces we add)

        func(f"X═{'═'*w}═X")
        func(f"║ {t}{' '*(w - len(t))} ║")
        func(f"╠═{'═'*w}═╣")
        func(f"║ {message}{' '*(w - len(message))} ║")
        func(f"X═{'═'*w}═X")

    def save_report(self, popup: bool = False) -> None:
        """
        Saves the report to a file.
        """
        if not self.file_path.name:
            raise RuntimeError("create_report() must be called before save_report().")
        try:
            notice = f"{self.name} report saved to: {self.file_path}"
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
    test.info("Only shown in logging, not reporting", log_only=True)
    test.info("Showing popup!", popup=True)
    test.debug("Debugging")
    test.error("Error")
    test.exception("Exception!")
    test.save_report()

    window.mainloop()
