# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
#
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.app.gui import AppWindow

# stdlib
from pathlib import Path
from tkinter import ttk
from tkinter.filedialog import askopenfilename

# third party
import ttkbootstrap as tkb
from ttkbootstrap.constants import (
    BOTH,
    BOTTOM,
    INDETERMINATE,
    LEFT,
    N,
    NO,
    RIGHT,
    S,
    TOP,
    X,
    Y,
    YES,
)
from ttkbootstrap.style import PRIMARY, SUCCESS
from ttkbootstrap.widgets.scrolled import ScrolledText

# local
from src.app.utils import WavePackFrame, PAD, PAD_X, PAD_Y, FONT_MONO
from src.kepware.controller import KepwareController, KepwareRequest, KepwareUi


class KepwareFrame(WavePackFrame):
    """
    Master controller of the Kepware CSV Comparison WavePack GUI and its object variables.

    Parameters
    ----------
    parent: tkb.Frame
        The main container owned by AppWindow
    window: tkb.Window
        A back reference to the root window
    """

    def __init__(self, parent: tkb.Frame, window: AppWindow) -> None:
        super().__init__(
            parent,
            height=525,
            height_min=525,
            width=850,
            width_min=850,
            resizable=(True, True),
        )
        self.window = window

        self.proc_ctrl: KepwareController = KepwareController(window)
        self.stext: ScrolledText

        # TK Variables options
        self.opt_input_1_path = tkb.StringVar(value="Select a file.")
        self.opt_input_2_path = tkb.StringVar(value="Select a file.")
        self.input_1_is_selected = tkb.BooleanVar(value=False)
        self.input_2_is_selected = tkb.BooleanVar(value=False)

        # Main content frame
        self.container = ttk.Frame(self, padding=PAD)
        self.container.pack(side=TOP, fill=BOTH, expand=YES)

        self._build_file_select()
        self._build_process_row()
        self._build_text_display()

        self.report.info(
            "Welcome to the WAVE. Start the process by choosing your files.", log=False
        )
        self.report.info("For more information please use the Help Menu.", log=False)

    @property
    def report(self):
        return self.window.controller.report

    def _build_file_select(self) -> None:
        """
        Builds the file selection widgets for the UI.
        """
        frame = tkb.Labelframe(
            self.container,
            text="Select your files.",
            padding=PAD,
        )
        frame.pack(side=TOP, anchor=N, fill=X, expand=NO)

        self._build_file_row(
            frame,
            "Select a Kepware CSV Export:",
            self.opt_input_1_path,
            self.input_1_is_selected,
            label_width=25,
        )
        self._build_file_row(
            frame,
            "Select another Kepware CSV Export:",
            self.opt_input_2_path,
            self.input_2_is_selected,
            label_width=35,
        )

    def _build_file_row(
        self,
        frame: tkb.Labelframe,
        label_text: str,
        path_variable: tkb.StringVar,
        is_selected: tkb.BooleanVar,
        label_width: int = 20,
        button_width: int = 20,
        file_types: tuple[str] = ("*.csv",),
    ):
        """
        Instantiates/Builds the file picking widgets for the UI.
        """
        row = tkb.Frame(frame, padding=PAD)
        row.pack(fill=X)
        label = tkb.Label(row, text=label_text, padding=PAD, width=label_width)
        label.pack(side=LEFT)
        entry = tkb.Entry(row, textvariable=path_variable)
        entry.pack(side=LEFT, fill=BOTH, expand=YES, padx=PAD_X)
        button = tkb.Button(
            row,
            text="Pick file",
            bootstyle=PRIMARY,
            padding=PAD,
            width=button_width,
            command=(
                lambda: self._set_filepath(
                    path_variable,
                    is_selected,
                    file_types,
                )
            ),
        )
        button.pack(side=RIGHT)

    def _set_filepath(
        self,
        string_variable: tkb.StringVar,
        is_selected: tkb.BooleanVar,
        file_types: tuple[str] | None = None,
    ) -> None:
        """
        Sets a file path string variable and updates the state tracking boolean.
        """
        if file_types is None:
            types = [
                ("Supported files", ("*.xlsx", "*.xlsm")),
            ]
        else:
            types = [
                ("Supported files", file_types),
            ]

        file_path = askopenfilename(title="Select a file.", filetypes=types)

        if file_path:
            string_variable.set(file_path)
            is_selected.set(True)
        else:
            string_variable.set("Cancelled")
            is_selected.set(False)

    def _build_text_display(self) -> None:
        """
        Builds the text display widgets for the UI.
        """
        frame = tkb.Labelframe(self.container, text="Process Output.")
        frame.pack(side=TOP, fill=BOTH, expand=YES)
        self.stext = ScrolledText(frame, height=24, font=FONT_MONO)
        self.stext.pack(side=TOP, fill=BOTH, padx=PAD_X, pady=PAD_Y, expand=YES)
        self.report.attach_text_display(self.stext)

    def _build_process_row(self) -> None:
        """
        Builds the footer row that holds the processing options and progress bar
        indicator.
        """
        frame = tkb.Labelframe(self.container, text="Process Status")
        frame.pack(side=BOTTOM, fill=X, anchor=S)

        self.progress_bar = tkb.Progressbar(frame, mode=INDETERMINATE)
        self.progress_bar.pack(side=LEFT, expand=YES, padx=PAD_X, pady=PAD_Y, fill=X)

        self.process_button = tkb.Button(
            frame,
            text="Compare",
            bootstyle=SUCCESS,
            padding=PAD,
            width=20,
            command=self._on_process_clicked,
        )
        self.process_button.pack(side=RIGHT, padx=PAD_X, pady=PAD_Y, fill=Y)

    def _on_process_clicked(self) -> None:
        """
        Builds the requests and ui objects to pass to the process thread when the
        process button is clicked.
        """
        if not (self.input_1_is_selected.get() and self.input_2_is_selected.get()):
            self.report.error("Please select both files to start process.")
            return

        if self.opt_input_1_path.get() == self.opt_input_2_path.get():
            self.report.error(
                "Both file selections contain the same path. "
                + "Please select different files."
            )
            return

        request = KepwareRequest(
            "Kepware Comparison",
            Path(self.opt_input_1_path.get()),
            Path(self.opt_input_2_path.get()),
        )

        ui = KepwareUi(
            self.progress_bar,
            self.process_button,
            self.stext,
        )

        self.proc_ctrl.start_process(request, ui)

    def on_teardown(self) -> None:
        """
        Called by AppWindow before the application closes.
        """
        pass
