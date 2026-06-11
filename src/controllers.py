# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
#
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH

"""
The controller class within this module is used to control the principle control flow
of the application.

Classes
-------
AppController
    Master App Controller

MTLController
    Master controller of reporting, processing, and configuration parsing.

MESController
    Master controller for the MES processor.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.gui import AppWindow

# stdlib
import json
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from threading import Thread
from tkinter.scrolledtext import ScrolledText

# third party
import ttkbootstrap as tkb
from ttkbootstrap.constants import NORMAL, DISABLED

# local
from src.paths import CONFIG_PATH, REPORTS_DIR
from src.mtl.process import Process
from src.reporting import Reporting


class ProcessType(int, Enum):
    NONE = 0
    COMPARE = 1
    APPEND = 2
    MES = 3


@dataclass(frozen=True)
class ProcessRequest:
    process_type: ProcessType
    filter: str
    data_table: str
    mtl_file_path: Path
    input_file_path: Path

    @property
    def report_name(self) -> str:
        return self.filter or "No_Filter"


@dataclass
class ProcessUi:
    progress_bar: tkb.Progressbar
    process_button: tkb.Button
    opt_process: tkb.IntVar
    stext: ScrolledText


class ProcessController:
    def __init__(self) -> None:
        self.process_thread: Thread | None = None


class AppController:
    """
    Master controller of the reporting and user configuration parsing.
    """

    def __init__(self, window: tkb.Window) -> None:
        self.window: tkb.Window = window
        self.user_configs: dict = self._load_user_configs()
        self.report: Reporting = self._set_report(window)

        # Set when process frame is created
        self.proc_ctrl: ProcessController | None = None

    def set_process_controller(self, controller: ProcessController) -> None:
        self.proc_ctrl = controller

    def _load_user_configs(self) -> dict:
        """
        Read the user configuration settings returned in a dict.
        """
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            try:
                cfg = json.load(f)
                return cfg
            except json.JSONDecodeError as e:
                raise json.JSONDecodeError(
                    f"Failed to parse config file at: {CONFIG_PATH}: {e.msg}",
                    e.doc,
                    e.pos,
                )
            except Exception as e:
                raise RuntimeError(
                    f"An unexptected error occurred while trying to load the user configuration file.\n{e}"
                )

    def _set_report(self, window: tkb.Window) -> Reporting:
        """
        Instantiates the main reporting class for the current process run.
        """
        return Reporting(
            window,
            REPORTS_DIR,
            verbose_printing=False,
            use_timestamps=self.user_configs.get("use_timestamps", False),  # type: ignore
            use_msg_types=self.user_configs.get("use_msg_types", False),  # type: ignore
        )

    def reset_report(
        self, text_display: ScrolledText, report_name: str = "New_Report_Not_Init"
    ) -> None:
        """
        Sets/creates a new report by re-initializing
        """
        if (
            self.proc_ctrl
            and self.proc_ctrl.process_thread
            and self.proc_ctrl.process_thread.is_alive()
        ):
            self.report.error(
                "Cannot update reporting settings while a process is running",
                popup=True,
            )
            return

        self.report = self._set_report(self.window)
        self.report.create_report(report_name)
        self.report.attach_text_display(text_display)

    def set_config_value(self, key: str, value: tkb.StringVar | tkb.BooleanVar) -> None:
        """
        Write a single user configuration through a dict key.
        """
        if (
            self.proc_ctrl
            and self.proc_ctrl.process_thread
            and self.proc_ctrl.process_thread.is_alive()
        ):
            value.set(self.user_configs.get(key, False))
            self.window.after(
                0,
                lambda: self.report.warning(
                    "Cannot change configurations while a process is running.",
                    popup=True,
                ),
            )
            return
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        cfg[key] = value.get()
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
        self.user_configs = self._load_user_configs()


class MTLController(ProcessController):
    """
    Master controller of the reporting, processing and configuration parsing.

    Attributes
    ----------
    window: tkb.Window
        a root window used to display the application

    Methods
    -------
    start_process(ProcessRequest, ProcessUI)
        Starts the data processing functions.
    """

    def __init__(self, window: AppWindow):
        super().__init__()
        self.window = window
        self._controller: AppController = window.controller

    def _start_thread(
        self,
        req: ProcessRequest,
        ui: ProcessUi,
    ) -> None:
        """
        Opens a new thread and starts the subroutine.
        """
        _started = time.perf_counter()
        try:
            process = Process(
                self._controller.report,
                req.filter,
                req.data_table,
                str(req.mtl_file_path),
                str(req.input_file_path),
            )

            if req.process_type == ProcessType.APPEND:
                self._controller.report.info("Appending data...")
                process.append_input()
            else:
                self._controller.report.info("Comparing data...")
                process.compare_input()

        except Exception as e:
            self._controller.report.exception(
                f"Subroutine process error:\n{e}",
                popup=True,
            )
        finally:
            _ended = time.perf_counter()
            self.window.after(
                0,
                lambda: self._controller.report.info(
                    "Subroutine ended.",
                    popup=True,
                ),
            )
            self.window.after(0, lambda: ui.progress_bar.stop())
            self.window.after(1, lambda: ui.opt_process.set(ProcessType.NONE.value))
            self.window.after(2, lambda: ui.process_button.config(state=NORMAL))
            completion_time = _ended - _started
            self._controller.report.simple_title(
                f"Processing took: {completion_time:.4f}s"
            )

    def start_process(
        self,
        req: ProcessRequest,
        ui: ProcessUi,
    ):
        """
        Starts the data processing functions.
        """
        if req.process_type == ProcessType.NONE:
            self.window.after(
                0,
                lambda: self._controller.report.error(
                    "Please select either the Compare or Append radio button.",
                    popup=True,
                ),
            )
            return

        if self.process_thread and self.process_thread.is_alive():
            self.window.after(
                0,
                lambda: self._controller.report.warning(
                    "Process already running!",
                    popup=True,
                ),
            )
            return

        ui.process_button.config(state=DISABLED)
        self._controller.reset_report(ui.stext, req.report_name)

        ui.progress_bar.start()

        self.process_thread = Thread(
            target=lambda: self._start_thread(req, ui),
            daemon=True,
        )
        self.process_thread.start()


class MESController(ProcessController):
    """
    Master controller of the MES process.
    """

    def __init__(self, window: AppWindow):
        super().__init__()
        self.window = window
        self._controller: AppController = window.controller

    def start_process(
        self,
        ui: ProcessUi,
    ):
        """
        Starts the data processing functions.
        """
        ui.progress_bar.start()
        self.process_thread = Thread(
            target=lambda: self._start_thread(ui),
            daemon=True,
        )
        self.process_thread.start()

    def _start_thread(
        self,
        ui: ProcessUi,
    ) -> None:
        """
        Opens a new thread and starts the subroutine.
        """
        try:
            self._controller.report.info("MES Process Test")
        except Exception as e:
            self._controller.report.exception(
                f"Subroutine process error:\n{e}",
                popup=True,
            )
        finally:
            self.window.after(
                0,
                lambda: self._controller.report.info(
                    "Subroutine ended.",
                    popup=True,
                ),
            )
            self.window.after(0, lambda: ui.progress_bar.stop())
            self.window.after(1, lambda: ui.opt_process.set(ProcessType.NONE.value))
            self.window.after(2, lambda: ui.process_button.config(state=NORMAL))
