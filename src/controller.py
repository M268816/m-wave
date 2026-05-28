# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
#
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH

"""
The controller class within this module is used to control the principle control flow
of the application.

Classes
-------
Controller
    Master controller of reporting, processing, and configuration parsing.
"""

# stdlib
import json
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
from src.process import Process
from src.reporting import Reporting


class ProcessType(int, Enum):
    NONE = 0
    COMPARE = 1
    APPEND = 2


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


class Controller:
    """
    Master controller of the reporting, processing and configuration parsing.

    Attributes
    ----------
    window: tkb.Window
        a root window used to display the application

    Methods
    -------
    set_config_value(key, value)
        writes a single configuration value to the json file.

    reset_report(text_display, filter_value)
        Sets/creates a new report by re-initializing

    start_process(req, ui)
        Starts the data processing functions.
    """

    def __init__(self, window: tkb.Window):
        self.root = window
        self.user_configs: dict = self._load_user_config()
        self.report: Reporting = self._set_report(self.root)
        self.process_thread: Thread | None = None

    def _load_user_config(self) -> dict:
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

    def _set_report(self, window) -> Reporting:
        """
        Instantiates the main reporting class for the current process run.
        """
        return Reporting(
            window,
            REPORTS_DIR,
            verbose_printing=False,
            use_timestamps=self.user_configs.get("use_timestamps"),  # type: ignore
            use_msg_types=self.user_configs.get("use_msg_types"),  # type: ignore
        )

    def set_config_value(self, key: str, value: tkb.StringVar | tkb.BooleanVar) -> None:
        """
        Write a single user configuration through a dict key.
        """
        if self.process_thread and self.process_thread.is_alive():
            value.set(self.user_configs.get(key, False))
            self.root.after(
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
        self.user_configs = self._load_user_config()

    def reset_report(self, text_display: ScrolledText, filter_string: str) -> None:
        """
        Sets/creates a new report by re-initializing
        """
        if self.process_thread and self.process_thread.is_alive():
            self.report.error(
                "Cannot update reporting settings while a process is running",
                popup=True,
            )
            return
        self.report = self._set_report(self.root)
        self.report.create_report(filter_string)
        self.report.attach_text_display(text_display)

    def start_process(
        self,
        req: ProcessRequest,
        ui: ProcessUi,
    ):
        """
        Starts the data processing functions.
        """
        if req.process_type == ProcessType.NONE:
            self.root.after(
                0,
                lambda: self.report.error(
                    "Please select either the Compare or Append radio button.",
                    popup=True,
                ),
            )
            return

        if self.process_thread and self.process_thread.is_alive():
            self.root.after(
                0,
                lambda: self.report.warning(
                    "Process already running!",
                    popup=True,
                ),
            )
            return

        ui.process_button.config(state=DISABLED)
        self.reset_report(ui.stext, req.report_name)

        ui.progress_bar.start()

        self.process_thread = Thread(
            target=lambda: self._start_thread(req, ui),
            daemon=True,
        )
        self.process_thread.start()

    def _start_thread(
        self,
        req: ProcessRequest,
        ui: ProcessUi,
    ) -> None:
        """
        Opens a new thread and starts the subroutine.
        """
        try:
            process = Process(
                self.report,
                req.filter,
                req.data_table,
                str(req.mtl_file_path),
                str(req.input_file_path),
            )

            if req.process_type == ProcessType.APPEND:
                self.report.info("Appending data...")
                process.append_input()
            else:
                self.report.info("Comparing data...")
                process.compare_input()

        except Exception as e:
            self.report.exception(
                f"Subroutine process error:\n{e}",
                popup=True,
            )
        finally:
            self.root.after(
                0,
                lambda: self.report.info(
                    "Subroutine ended.",
                    popup=True,
                ),
            )
            self.root.after(0, lambda: ui.progress_bar.stop())
            self.root.after(0, lambda: ui.opt_process.set(ProcessType.NONE.value))
            self.root.after(0, lambda: ui.process_button.config(state=NORMAL))
