# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
#
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.app.gui import AppWindow

# stdio
from tkinter.filedialog import askopenfilename

# third-party
import ttkbootstrap as tkb
from ttkbootstrap.constants import (
    TOP,
    BOTH,
    NSEW,
    X,
    NO,
    LEFT,
    PRIMARY,
    RIGHT,
    YES,
    BOTTOM,
    S,
    INDETERMINATE,
)

# local
from src.app.utils import ProtocolFrame, PAD, PAD_X, PAD_Y
from src.tag_formatter.controller import TagFormatterController


class TagFormatterFrame(ProtocolFrame):
    def __init__(self, parent: tkb.Frame, window: AppWindow) -> None:
        super().__init__(parent)
        self.window = window
        self.proc_ctrl: TagFormatterController = TagFormatterController(window)

        self.container = tkb.Frame(self, padding=PAD)
        self.container.pack(side=TOP, fill=BOTH, expand=True)

        self.opt_plc_file_path = tkb.StringVar()
        self.opt_tag_file_path = tkb.StringVar()

        self._plc_list_selected = tkb.BooleanVar(value=False)
        self._tag_list_selected = tkb.BooleanVar(value=False)

        self.tag_form_rows: int = 0

        self._build_footer()  # Building the footer first ensures its bottom sticky
        self._build_file_inputs()
        self._build_tag_form()

    @property
    def report(self):
        return self.window.controller.report

    def _build_footer(self) -> None:
        """
        Builds the footer row that holds the processing options and progress bar
        indicator.
        """
        frame = tkb.Labelframe(self.container, text="Process Status")
        frame.pack(side=BOTTOM, fill=X, anchor=S, padx=PAD_X, pady=PAD_Y)

        self.progress_bar = tkb.Progressbar(frame, mode=INDETERMINATE)
        self.progress_bar.pack(side=LEFT, expand=YES, padx=PAD_X, pady=PAD_Y, fill=X)

        # self.radio_append = tkb.Radiobutton(
        #     frame,
        #     text="Append",
        #     variable=self.opt_process,
        #     value=MTLProcessorType.APPEND.value,
        # )
        # self.radio_append.pack(side=LEFT, padx=PAD_X, pady=PAD_Y, fill=Y)
        #
        # self.radio_compare = tkb.Radiobutton(
        #     frame,
        #     text="Compare",
        #     variable=self.opt_process,
        #     value=MTLProcessorType.COMPARE.value,
        # )
        # self.radio_compare.pack(side=LEFT, padx=PAD_X, pady=PAD_Y, fill=Y)

        self.process_button = tkb.Button(
            frame,
            text="Process",
            bootstyle=SUCCESS,
            padding=PAD,
            width=20,
            command=self._on_process_clicked,
        )
        self.process_button.pack(side=RIGHT, padx=PAD_X, pady=PAD_Y, fill=Y)
        pass

    def _on_process_clicked(self) -> None:
        """
        Builds the requests and ui objects to pass to the process thread when the
        process button is clicked.
        """
        if not (self._plc_list_selected.get() and self._tag_list_selected.get()):
            self.report.error("Please select both files to start process.")
            return

        # req = MTLRequest(
        #     MTLProcessorType(self.opt_process.get()),
        #     self.opt_filter.get(),
        #     self.opt_data_table.get(),
        #     Path(self.opt_mtl_path.get()),
        #     Path(self.opt_input_path.get()),
        # )
        # ui = MTLUi(
        #     self.progress_bar,
        #     self.process_button,
        #     self.opt_process,
        #     self.stext,
        # )

        self.proc_ctrl.start_process(req, ui)

    def _build_file_inputs(self) -> None:
        """
        Builds the file selection widgets for the UI.
        """
        frame = tkb.Labelframe(
            self.container,
            text="Select your files.",
            padding=PAD,
        )
        frame.pack(side=TOP, fill=BOTH, padx=PAD_X, pady=PAD_Y, expand=NO)

        self._build_file_row(
            frame,
            "Input PLC Tag List:",
            self.opt_plc_file_path,
            self._plc_list_selected,
        )
        self._build_file_row(
            frame,
            "Input Kepware Tag List:",
            self.opt_tag_file_path,
            self._tag_list_selected,
        )

    def _build_file_row(
        self,
        frame: tkb.Labelframe,
        label_text: str,
        path_variable: tkb.StringVar,
        is_selected: tkb.BooleanVar,
        width: int = 20,
        file_types: tuple[str] | None = None,
    ):
        """
        Instantiates/Builds the file picking widgets for the UI.
        """
        row = tkb.Frame(frame, padding=PAD)
        row.pack(fill=X)
        label = tkb.Label(row, text=label_text, padding=PAD, width=width)
        label.pack(side=LEFT)
        entry = tkb.Entry(row, textvariable=path_variable)
        entry.pack(side=LEFT, fill=BOTH, expand=YES, padx=PAD_X)
        button = tkb.Button(
            row,
            text="Pick file",
            bootstyle=PRIMARY,
            padding=PAD,
            width=width,
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
                ("Supported files", ("*.xlsx", "*.xlsm", "*.csv")),
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

    def _build_tag_form(self) -> None:
        """
        Holds the form creation fuctions
        """
        self.tag_form = tkb.Labelframe(
            self.container, text="Tag Formatter", padding=PAD
        )
        self.tag_form.pack(side=TOP, fill=BOTH, padx=PAD_X, pady=PAD_Y)
        self.tag_form.columnconfigure(0, weight=0)
        self.tag_form.columnconfigure(1, weight=1)

        self.equipment_code_var, self.equipment_code_wid = self._entry_row(
            "Equipment Code",
        )
        self.kepware_channel_var, self.kepware_channel_wid = self._entry_row(
            "Kepware Channel"
        )
        self.kepware_device_var, self.kepware_device_wid = self._entry_row(
            "Kepware Device"
        )
        self.department_code_var, self.department_code_wid = self._entry_row(
            "Department Code Device"
        )
        self.tag_length_var, self.tag_length_wid = self._int_row(
            "Pi Tag Prefix Length", default_value=15
        )
        self.node_id_var, self.node_id_wid = self._entry_row(
            "NodeId Prefix", default_value="ns=2;s="
        )
        self.namespace_index_var, self.namespace_index_wid = self._int_row(
            "NamespaceIndex", default_value=2
        )

    def _entry_row(
        self, label_text: str, default_value: str = ""
    ) -> tuple[tkb.StringVar, tkb.Entry]:
        """
        Build a form row with a label and entry widget, uses a tkb.StringVar for
        controlling and accessing the entry.

        returns tuple[tkb.StringVar, tkb.Entry]
        """
        var = tkb.StringVar(value=default_value)

        lab = tkb.Label(self.tag_form, text=label_text)
        lab.grid(row=self.tag_form_rows, column=0, padx=PAD_X, pady=PAD_Y, sticky=NSEW)

        wid = tkb.Entry(self.tag_form, textvariable=var)
        wid.grid(row=self.tag_form_rows, column=1, padx=PAD_X, pady=PAD_Y, sticky=NSEW)
        self.tag_form_rows += 1
        return var, wid

    def _int_row(
        self, label_text: str, default_value: int = 0
    ) -> tuple[tkb.StringVar, tkb.Spinbox]:
        """
        Build a form row with a label and entry widget, uses a tkb.StringVar for
        controlling and accessing the entry.

        returns tuple[tkb.StringVar, tkb.Entry]
        """
        var = tkb.StringVar(value=str(default_value))

        lab = tkb.Label(self.tag_form, text=label_text)
        lab.grid(row=self.tag_form_rows, column=0, padx=PAD_X, pady=PAD_Y, sticky=NSEW)

        wid = tkb.Spinbox(
            self.tag_form,
            textvariable=var,
            from_=0,
            to=100,
            increment=1,
        )
        wid.grid(row=self.tag_form_rows, column=1, padx=PAD_X, pady=PAD_Y, sticky=NSEW)
        self.tag_form_rows += 1
        return var, wid
