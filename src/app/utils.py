# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
#
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH

# stdio
import getpass
import json
from threading import Thread
import tkinter as tk
from tkinter import font
from pathlib import Path
import warnings

# third party
import ttkbootstrap as tkb

# local
from src.app.paths import PATHS

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
def get_user_prefs() -> Path:
    """
    Returns the user preferences path. If the user preferences do not exist,
    it creates them form the default assets.
    """
    user_prefs_path = PATHS.user_prefs_dir / "user_preferences.json"
    if user_prefs_path.exists():
        return user_prefs_path

    default_path = PATHS.assets_dir / "user_preferences.json"

    if default_path.exists():
        with open(default_path, "r", encoding="utf-8") as f:
            default_prefs = json.load(f)

        with open(user_prefs_path, "w", encoding="utf-8") as f:
            json.dump(default_prefs, f, indent=2)
    else:
        warnings.warn(
            "Could not create a user preferences path! Using defaults, but cannot save user settings.",
            RuntimeWarning,
            stacklevel=2,
        )
        return default_path

    return user_prefs_path


USER_PREFS_PATH = get_user_prefs()


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


class ProcessController:
    """
    Class helper for type assignment
    """

    def __init__(self) -> None:
        self.process_thread: Thread | None = None


class WavePackFrame(tkb.Frame):
    """
    Class helper for type assignment
    """

    def __init__(
        self,
        parent: tkb.Frame,
        height: int,
        height_min: int,
        width: int,
        width_min: int,
        resizable: tuple[bool, bool],
    ) -> None:
        super().__init__(parent)
        self.proc_ctrl: ProcessController
        self.height = height
        self.height_min = height_min
        self.width = width
        self.width_min = width_min
        self.resizable = resizable
        self.help_label: str = "Instructions"  # default, override per frame

    @property
    def has_help(self) -> bool:
        """
        Returns True if this frame has overridden show_help.
        AppWindow uses this to decide whether to show the help menu item at all.
        """
        return type(self).show_help is not WavePackFrame.show_help

    def show_help(self) -> None:
        """
        Override in subclasses to display frame-specific help instructions.
        Default is a no-op if not overridden, the help menu item is hidden.
        """
        pass

    def on_teardown(self) -> None:
        """
        Called by AppWindow before the application closes.
        """
        return None
