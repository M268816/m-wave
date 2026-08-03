# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
#
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH

# stdio
import getpass
import json
import tkinter as tk
from tkinter import font
from pathlib import Path
import warnings

# third party
import ttkbootstrap as tkb

# local
from m_wave.core.paths import PATHS

# SIMPLE CONSTANTS
H1 = ("Verdana", 20, font.BOLD)
H2 = ("Verdana", 16, font.NORMAL)
H3 = ("Verdana", 14, font.NORMAL)
H4 = ("Verdana", 12, font.NORMAL)
FONT = ("Verdana", 10, font.NORMAL)
FONT_SMALL = ("Verdana", 8, font.NORMAL)
FONT_SMALLER = ("Verdana", 7, font.NORMAL)
_MONO = "Consolas"
FONT_MONO = (_MONO, 10, font.NORMAL)
FONT_MONO_SMALL = (_MONO, 8, font.NORMAL)
FONT_MONO_SMALLER = (_MONO, 7, font.NORMAL)
FONT_MONO_BIG = (_MONO, 12, font.NORMAL)
FONT_MONO_BIGGER = (_MONO, 14, font.NORMAL)

PAD_X = 4
PAD_Y = 4
PAD = 4

USER = getpass.getuser()
DATETIME_FORMAT = "%Y-%m-%dT%H_%M_%SZ"
DATETIME_FORMAT_MERCK = "%d-%b-%Y %H:%M:%S"


# COMPUTED CONSTANTS
def get_user_prefs_path() -> Path:
    """
    Returns the user preferences path. If the generated user preferences do not
    exist, create them form the default assets first.
    """
    user_prefs_path = PATHS.user_preferences_path
    default_prefs_path = PATHS.user_preferences_template_path

    if user_prefs_path.exists():
        return user_prefs_path

    if not default_prefs_path.exists():
        warnings.warn(
            f"Default user preferences template not found at: {default_prefs_path}. "
            f"User preferences could not be initialized at : {user_prefs_path}",
            RuntimeWarning,
            stacklevel=2,
        )
        return user_prefs_path

    try:
        PATHS.user_preferences_dir.mkdir(parents=True, exist_ok=True)

        with open(default_prefs_path, "r", encoding="utf-8") as f:
            default_prefs = json.load(f)

        with open(user_prefs_path, "w", encoding="utf-8") as f:
            json.dump(default_prefs, f, indent=2)

        return user_prefs_path
    except Exception as e:
        warnings.warn(
            f"Could not create user preferences at: {user_prefs_path}. "
            f"Using defaults for this session. Error: {e}",
            RuntimeWarning,
            stacklevel=2,
        )
        return user_prefs_path

# UTILS
def get_window_scale_factor(
    window: tkb.Window,
    base_height: int = 1080,
) -> float:
    """
    Returns a scaled factor to the active screen height based on a 1080p baseline.
    """
    window.update_idletasks()
    screen_height = window.winfo_screenheight()
    scale_factor = screen_height / base_height
    return scale_factor


def _get_scaled_geometry(
    window: tkb.Window,
    width: int,
    height: int,
    base_height: int,
) -> tuple[int, int]:
    """
    Returns a scaled width and height to the active screen based on a 1080p baseline.
    """
    scale_factor = get_window_scale_factor(window=window, base_height=base_height)
    scaled_width = int(width * scale_factor)
    scaled_height = int(height * scale_factor)
    return scaled_width, scaled_height


def apply_scaled_geometry(
    window: tkb.Window,
    width: int,
    height: int,
    base_height: int = 1080,
    delay: int = 500,
) -> None:
    """
    Apply a deferred scaled window geometry to for the active monitor.
    """
    scaled_w, scaled_h = _get_scaled_geometry(window, width, height, base_height)
    window.after(delay, lambda: window.geometry(f"{scaled_w}x{scaled_h}"))


def create_geometry_display(
    window: tkb.Window,
    parent_frame: tkb.Frame,
    width: int,
    height: int,
    base_height=1080,
):
    """
    Creates a widget that will display the current window dimensions for debugging.
    """
    frame = tkb.Frame(parent_frame, padding=PAD)
    frame.pack(side="top", fill="x", expand=True, padx=PAD_X, pady=PAD_Y)

    s_width, s_height = _get_scaled_geometry(window, width, height, base_height)

    target_label = tkb.Label(
        frame, font=H2, text=f"Target {width}x{height} | Scaled: {s_width}x{s_height}"
    )
    target_label.pack(side="left")

    live_var = tkb.StringVar(value="Live: ...")
    live_label = tkb.Label(frame, font=H2, textvariable=live_var)
    live_label.pack(side="left")

    def _update_live(event: tk.Event) -> None:
        if event.widget is window:
            live_var.set(f"Live: {event.width}x{event.height}")

    window.bind("<Configure>", _update_live, add="+")


def load_configs(config_path: Path) -> dict:
    """
    Load a configuration for user options of a WavePack. Usually used in the
    root/AppWindow. Returns a dict of settings.
    """
    with open(config_path, "r", encoding="utf-8") as f:
        try:
            cfg = json.load(f)
            return cfg
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(
                f"Failed to decode file at: {config_path}: {e.msg}",
                e.doc,
                e.pos,
            )
        except Exception as e:
            raise RuntimeError(
                f"An unexpected error occurred while trying to load the configuration file.\n{e}"
            )


def set_config_value(
    config_path: Path,
    config_variable: dict,
    key: str,
    value: tkb.StringVar | tkb.BooleanVar,
) -> bool:
    """
    Write a single user configuration through a dict key.
    Returns True if the value was written. Raises runtime error if it fails.
    Warning: will mutate the given config_variable with new data.
    """
    # Move this logic to the caller
    # if proc_ctrl and proc_ctrl.process_thread and proc_ctrl.process_thread.is_alive():
    #     # If there is a process controller, it has a thread, and the thread is alive
    #     # Set the widget to the previous value, denying the change
    #     value.set(config_variable.get(key, False))
    #
    #     window.after(
    #         0,
    #         lambda: self.report.warning(
    #             "Cannot change configurations while a process is running.",
    #             popup=True,
    #         ),
    #     )
    #     return False
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        cfg[key] = value.get()
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
        config_variable.clear()
        config_variable.update(cfg)
        return True
    except Exception as e:
        raise RuntimeError(f"Could not set the configuration.\n{e}")