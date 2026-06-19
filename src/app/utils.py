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
APP_SIZE = (850, 525)
APP_MINSIZE = (850, 525)

H1 = ("Verdana", 20, font.BOLD)
H2 = ("Verdana", 16, font.NORMAL)
H3 = ("Verdana", 14, font.NORMAL)
H4 = ("Verdana", 12, font.NORMAL)
FONT = ("Verdana", 10, font.NORMAL)

PAD_X = 8
PAD_Y = 8
PAD = 8

USER = getpass.getuser()
DATETIME_FORMAT = "%Y-%m-%dT%H_%M_%SZ"
DATETIME_FORMAT_MERCK = "%d-%b-%Y %H:%M:%S"


class ProcessController:
    """
    Class helper for type assignment
    """

    def __init__(self) -> None:
        self.process_thread: Thread | None = None


class ProtocolFrame(tkb.Frame):
    """
    Class helper for type assignment
    """

    def __init__(self, parent: tkb.Frame) -> None:
        super().__init__(parent)
        self.proc_ctrl: ProcessController

    def on_teardown(self) -> None:
        return None
