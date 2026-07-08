# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
#
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH

# stdio
import getpass
from threading import Thread
from tkinter import font

# third party
import ttkbootstrap as tkb

# local

# CONSTANTS
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

PAD_X = 8
PAD_Y = 8
PAD = 8

USER = getpass.getuser()
DATETIME_FORMAT = "%Y-%m-%dT%H_%M_%SZ"
DATETIME_FORMAT_MERCK = "%d-%b-%Y %H:%M:%S"


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

    def on_teardown(self) -> None:
        """
        Called by AppWindow before the application closes.
        """
        return None
