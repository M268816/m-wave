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

"""

# stdlib
import json

# third party
import ttkbootstrap as tkb
from ttkbootstrap.widgets.scrolled import ScrolledText

# local
from src.app.paths import CONFIG_PATH, REPORTS_DIR
from src.app.reporting import Reporting
from src.app.utils import ProcessController


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
