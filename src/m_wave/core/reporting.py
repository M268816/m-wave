# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
##
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH

# stdlib
import logging
import textwrap
from queue import Queue
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

# third party
import ttkbootstrap as tkb
from ttkbootstrap.dialogs import Messagebox as modal
from ttkbootstrap.constants import DISABLED, END, NORMAL
from ttkbootstrap.widgets.scrolled import ScrolledText

# local
from m_wave.core.utils import DATETIME_FORMAT, DATETIME_FORMAT_MERCK, USER

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LogConfig:
    logger_func: Callable
    modal_func: Callable
    msg_type: str
    modal_title: str


_CRITICAL_CONFIG: LogConfig = LogConfig(
    logger.critical, modal.show_error, "CRITICAL", "CRITICAL FAILURE"
)
_DEBUG_CONFIG: LogConfig = LogConfig(
    logger.debug, modal.show_error, "DEBUG", "Debugger"
)

_ERROR_CONFIG: LogConfig = LogConfig(
    logger.error, modal.show_error, "ERROR", "An error has occurred!"
)
_EXCEPTION_CONFIG: LogConfig = LogConfig(
    logger.exception, modal.show_error, "EXCEPTION", "An exception was thrown!"
)
_INFO_CONFIG: LogConfig = LogConfig(
    logger.info, modal.show_info, "INFO", "You should know..."
)
_WARNING_CONFIG: LogConfig = LogConfig(
    logger.warning, modal.show_warning, "WARNING", "Warning!"
)


class Reporting:
    """
    A class that creates a report for a single process run by the app. It appends
    lines of strings to a list and writes them to a text file. Lines will also
    be added to the log file associated with the main logger.
    """

    def __init__(
        self,
        parent_window: tkb.Window,
        output_dir: Path,
        verbose_printing: bool = True,
        populate_report: bool = True,
        populate_log: bool = True,
        use_timestamps: bool = True,
        use_msg_types: bool = True,
        timestamp: datetime | None = None,
    ) -> None:
        self.name = ""
        self.text_display: ScrolledText | None = None
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
        self.user = USER

        if timestamp:
            self.timestamp = timestamp
        else:
            self.timestamp = datetime.now().strftime(DATETIME_FORMAT)
        self.timestamp_merck = datetime.now().strftime(DATETIME_FORMAT_MERCK)

        self.report_lines = []
        self._modal_queue = Queue()
        self._modal_busy = False

    def attach_text_display(self, text_display: ScrolledText) -> None:
        """
        Attach a ScrolledText widget to the reporting instance for live updates.
        """
        self.text_display = text_display

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
                self._modal_busy = True
                self.parent_window.after(0, self._show_next_modal)

    def _add_line(self, msg: str, msg_type: str | None = None) -> None:
        """
        Private function that adds a single string line to the report buffer.
        Lines over max_len chars are wrapped and appended individually.
        """
        max_len = self.width

        if msg_type is None:
            msg_type = "UNKNOWN"

        timestamp = datetime.now().strftime(DATETIME_FORMAT)

        prefix = ""

        diff = max(0, len("EXCEPTION") - len(msg_type))
        type_padding = " " * diff

        if self.use_timestamps:
            prefix = f"{timestamp}:"
        if self.use_msg_types:
            prefix += f"{msg_type}" + type_padding + "❚┋❚"

        prefix_len = len(prefix)
        indent = " " * prefix_len

        wrapped_lines = textwrap.wrap(msg, width=max_len) if msg else [""]

        for i, chunk in enumerate(wrapped_lines):
            if i == 0:
                self.report_lines.append(f"{prefix}{chunk}")
            else:
                self.report_lines.append(f"{indent}{chunk}")

    def create_report(
        self,
        new_name: str,
        new_timestamp: datetime | None = None,
        update_dirs: bool = True,
    ) -> None:
        """
        Name the report and by default initialize the directories.
        """
        self.report_lines = []

        self.timestamp = (
            new_timestamp.strftime(DATETIME_FORMAT)
            if new_timestamp
            else datetime.now().strftime(DATETIME_FORMAT)
        )

        self.name = new_name.strip() or "No_Filter"
        # NOTE: "*my report"

        self.cleaned_name = self.name.replace(" ", "_")
        self.cleaned_name = self.cleaned_name.replace("*", "")
        # NOTE: "my_report"

        self.report_name = f"{self.timestamp}_({self.cleaned_name})"
        # NOTE: "TIMESTAMP_(my_report)"

        self.report_folder = self.output_dir / self.report_name
        if update_dirs:
            self.report_folder.mkdir(parents=True, exist_ok=True)
        # NOTE: "BASE_DIR\TIMESTAMP_(my_report)"

        report_path = self.report_folder / self.cleaned_name
        # NOTE: "BASE_DIR\TIMESTAMP_my_report\my_report"

        self.file_path = report_path.with_suffix(".log")
        # NOTE: "BASE_DIR\TIMESTAMP_my_report\my_report.log"

    def _emit(
        self,
        msg: str,
        config: LogConfig,
        report: bool | None,
        log: bool | None,
        verbose: bool | None,
        popup: bool,
    ) -> None:
        """
        A helper function that pushes report logging lines to pre-configured outputs.
        """
        _log = self.logging if log is None else log
        _verbose = self.verbose if verbose is None else verbose
        _report = self.report if report is None else report

        if _log:
            config.logger_func(msg)
        if _verbose:
            print(msg)
        if _report:
            self._add_line(msg, config.msg_type)
            if self.text_display is not None:
                self._handle_text_display(msg)
        if popup:
            self._queue_modal(config.modal_func, msg, config.modal_title)

    def _handle_text_display(self, msg) -> None:
        """
        Write a message to the text_display (ScrolledText) on the main thread.
        """
        if self.text_display is None:
            return

        def _write() -> None:
            tw = self.text_display.text  # type: ignore
            tw.configure(state=NORMAL)  # type: ignore
            tw.insert(END, msg + "\n")
            tw.configure(state=DISABLED)  # type: ignore

            tw.see(END)

        self.parent_window.after(0, _write)

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
        self._emit(
            msg=msg,
            config=_CRITICAL_CONFIG,
            report=report,
            log=log,
            verbose=verbose,
            popup=popup,
        )

    def debug(
        self,
        msg: str,
        report: bool | None = None,
        log: bool | None = None,
        verbose: bool | None = None,
        popup: bool = False,
    ) -> None:
        """
        Print, log, and report debug information.
        """
        self._emit(
            msg=msg,
            config=_DEBUG_CONFIG,
            report=report,
            log=log,
            verbose=verbose,
            popup=popup,
        )

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
        self._emit(
            msg=msg,
            config=_ERROR_CONFIG,
            report=report,
            log=log,
            verbose=verbose,
            popup=popup,
        )

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
        self._emit(
            msg=msg,
            config=_EXCEPTION_CONFIG,
            report=report,
            log=log,
            verbose=verbose,
            popup=popup,
        )

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
        self._emit(
            msg=msg,
            config=_INFO_CONFIG,
            report=report,
            log=log,
            verbose=verbose,
            popup=popup,
        )

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
        self._emit(
            msg=msg,
            config=_WARNING_CONFIG,
            report=report,
            log=log,
            verbose=verbose,
            popup=popup,
        )

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
        self.error("~" * (self.width // 2))

    def save_report(self, popup: bool = False) -> None:
        """
        Saves the report to a file.
        """
        if not self.file_path.name:
            raise RuntimeError("create_report() must be called before save_report().")
        try:
            notice = f"{self.name} report saved to: ..//{self.file_path.name}"
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
