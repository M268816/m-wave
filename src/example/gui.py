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
from tkinter.filedialog import askopenfilename

# third party
import ttkbootstrap as tkb
from ttkbootstrap.constants import (
    Y,
    X,
    TOP,
    BOTH,
    CENTER,
    YES,
    NO,
    BOTTOM,
    INDETERMINATE,
    N,
    S,
    LEFT,
    RIGHT,
    SUCCESS,
    PRIMARY,
)
from ttkbootstrap.dialogs import Messagebox
from ttkbootstrap.scrolled import ScrolledText

# local
from src.app.reporting import Reporting
from src.app.utils import WavePackFrame, PAD, PAD_X, PAD_Y, FONT_MONO
from src.example.controller import ExampleController, ExampleRequest, ExampleUi
from src.example.paths import EXAMPLE_INSTRUCTIONS_PATH

with open(EXAMPLE_INSTRUCTIONS_PATH, "r", encoding="utf-8") as f:
    INSTRUCTIONS = f.read()


class ExampleFrame(WavePackFrame):
    def __init__(
        self,
        parent: tkb.Frame,
        window: AppWindow,
    ) -> None:
        super().__init__(
            parent,
            height=480,
            height_min=480,
            width=700,
            width_min=700,
            resizable=(True, True),
        )
        self.window = window
        self.help_label = "Example"
        self.proc_ctrl: ExampleController = ExampleController(window)

        self.opt_input_path = tkb.StringVar()
        self.input_is_selected = tkb.BooleanVar()

        self.container = tkb.Frame(self, padding=PAD)
        self.container.pack(side=TOP, fill=BOTH, expand=True)

        self._build_footer()
        # Building the footer first ensures it sticks to the bottom of the container

        self._build_simple_display()
        self._build_file_select()
        self._build_text_display()

    @property
    def report(self) -> Reporting:
        return self.window.controller.report

    def show_help(self) -> None:
        self.report.info(
            "Instructions will be displayed.", log=False, verbose=False, popup=True
        )
        self.report.info(INSTRUCTIONS, log=False, verbose=False, popup=True)

    def _build_simple_display(self) -> None:
        self.label_var = tkb.StringVar(value="Hello, World.")
        self.label = tkb.Label(
            self.container,
            textvariable=self.label_var,
            background="yellow",
            justify=CENTER,
            anchor=CENTER,
        )
        self.label.pack(
            expand=True,
            fill=X,
            side=TOP,
        )

        self.button_var = tkb.StringVar(value="Click me.")
        self.simple_button = tkb.Button(
            self.container,
            textvariable=self.button_var,
            padding=PAD,
            width=32,
            command=self._on_button_pressed,
        )
        self.simple_button.pack(side=TOP)

    def _on_button_pressed(self) -> None:
        Messagebox.ok(title="Hello", message="You pressed the button!")

    def _build_file_select(self) -> None:
        """
        Builds the file selection widgets for the UI.
        """
        frame = tkb.Labelframe(
            self.container,
            text="Select a file.",
            padding=PAD,
        )
        frame.pack(side=TOP, anchor=N, fill=X, expand=NO)

        self._build_file_row(
            frame,
            "Select a file:",
            self.opt_input_path,
            self.input_is_selected,
            label_width=25,
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

    def _build_footer(self) -> None:
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
            text="Example",
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
        if not self.input_is_selected.get():
            self.report.error("Please select a file to start processing.")
            return

        request = ExampleRequest(
            "Example Report",
            Path(self.opt_input_path.get()),
        )

        ui = ExampleUi(
            self.progress_bar,
            self.process_button,
            self.stext,
        )

        self.proc_ctrl.start_process(request, ui)
