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
from pathlib import Path

# third party
import ttkbootstrap as tkb
from ttkbootstrap.widgets.scrolled import ScrolledText

# local
from src.app.paths import PATHS
from src.app.reporting import Reporting
from src.app.utils import ProcessController, USER_PREFS_PATH


class AppController:
    """
    Master controller of the reporting and user configuration parsing.
    """

    def __init__(self, window: tkb.Window) -> None:
        self.window: tkb.Window = window
        self.user_preferences: dict = self._load_configs(USER_PREFS_PATH)
        # TODO: This should be moved to the MTL WavePack I think.
        mtl_config_path = PATHS.assets_dir / "mtl_config.json"
        self.mtl_configs: dict = self._load_configs(mtl_config_path)
        self.report_dir = PATHS.reports_dir
        self.report: Reporting = self._set_report(window)

        # Set when process frame is created
        self.proc_ctrl: ProcessController | None = None

    def set_process_controller(self, controller: ProcessController) -> None:
        self.proc_ctrl = controller

    def _load_configs(self, path: Path) -> dict:
        """
        Read a configuration setting file and return a dict of settings.
        """
        with open(path, "r", encoding="utf-8") as f:
            try:
                cfg = json.load(f)
                return cfg
            except json.JSONDecodeError as e:
                raise json.JSONDecodeError(
                    f"Failed to parse file at: {path}: {e.msg}",
                    e.doc,
                    e.pos,
                )
            except Exception as e:
                raise RuntimeError(
                    f"An unexptected error occurred while trying to load the configuration file.\n{e}"
                )

    def _set_report(self, window: tkb.Window) -> Reporting:
        """
        Instantiates the main reporting class for the current process run.
        """
        return Reporting(
            window,
            self.report_dir,
            verbose_printing=False,
            use_timestamps=self.user_preferences.get("use_timestamps", False),  # type: ignore
            use_msg_types=self.user_preferences.get("use_msg_types", False),  # type: ignore
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

    def set_config_value(
        self,
        config_path: Path,
        config_variable: dict,
        key: str,
        value: tkb.StringVar | tkb.BooleanVar,
    ) -> bool:
        """
        Write a single user configuration through a dict key.
        Returns True if the value was written.
        Returns False if blocked by running process.
        """
        if (
            self.proc_ctrl
            and self.proc_ctrl.process_thread
            and self.proc_ctrl.process_thread.is_alive()
        ):
            # If there is a process controller, it has a thread, and the thread is alive
            # Set the widget to the previous value, denying the change
            value.set(config_variable.get(key, False))

            self.window.after(
                0,
                lambda: self.report.warning(
                    "Cannot change configurations while a process is running.",
                    popup=True,
                ),
            )
            return False

        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        cfg[key] = value.get()

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)

        config_variable = self._load_configs(config_path)

        return True
