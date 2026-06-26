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
    Y,
    SUCCESS,
    CENTER,
)
from ttkbootstrap.scrolled import ScrolledText

# local
from src.app.utils import FONT, WavePackFrame, PAD, PAD_X, PAD_Y, FONT_MONO
from src.tag_doc_gen.controller import (
    TagDocGenController,
    TagDocGenRequest,
    TagDocGenUi,
    TagGeneratorType,
)


class TagDocGenFrame(WavePackFrame):
    def __init__(self, parent: tkb.Frame, window: AppWindow) -> None:
        super().__init__(
            parent,
            height=640,
            height_min=640,
            width=640,
            width_min=640,
            resizable=(True, True),
        )
        self.window = window
        self.proc_ctrl: TagDocGenController = TagDocGenController(window)

        self.container = tkb.Frame(self, padding=PAD)
        self.container.pack(side=TOP, fill=BOTH, expand=True)

        self.opt_input_file_path = tkb.StringVar()
        self.input_is_selected = tkb.BooleanVar(value=False)
        self.generator_option = tkb.StringVar(value=TagGeneratorType.NONE.value)

        self.tag_form_rows: int = 0

        self._build_footer()
        self._build_header()
        self._build_file_inputs()
        self._build_tag_form()
        self._build_text_display()

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

        generator_options = [gen_type.value for gen_type in TagGeneratorType]

        self.gen_opt_cbox = tkb.Combobox(frame, values=generator_options, width=25)
        self.gen_opt_cbox.pack(side=LEFT, padx=PAD_X)
        self.gen_opt_cbox.current(0)
        self.gen_opt_cbox.bind("<<ComboboxSelected>>", self._on_gen_opt_selected)

        self.process_button = tkb.Button(
            frame,
            text="Generate",
            bootstyle=SUCCESS,
            padding=PAD,
            width=20,
            command=self._on_process_clicked,
        )
        self.process_button.pack(side=RIGHT, padx=PAD_X, pady=PAD_Y, fill=Y)
        pass

    def _on_gen_opt_selected(self, event) -> None:
        """
        Gets the new table selection and sets the generator option when its combo box
        is changed.
        """
        _ = event
        val = self.gen_opt_cbox.get()
        self.generator_option.set(val)

    def _on_process_clicked(self) -> None:
        """
        Builds the requests and ui objects to pass to the process thread when the
        process button is clicked.
        """
        if not self.input_is_selected:
            self.report.error("Please select a file to start the process.")
            return

        if self.gen_opt_cbox.get() == TagGeneratorType.NONE.value:
            self.report.error("Please select a document to generate.")

        req = TagDocGenRequest(
            self.gen_opt_cbox.get(),
            self.equipment_code_var,
            self.kepware_channel_var,
            self.kepware_device_var,
            self.department_code_var,
            self.tag_length_var,
            self.node_id_var,
            self.namespace_index_var,
            TagGeneratorType(self.generator_option.get()),
        )

        ui = TagDocGenUi(
            self.equipment_code_wid,
            self.kepware_channel_wid,
            self.kepware_device_wid,
            self.department_code_wid,
            self.tag_length_wid,
            self.node_id_wid,
            self.namespace_index_wid,
            self.progress_bar,
            self.gen_opt_cbox,
            self.stext,
            self.process_button,
        )

        self.proc_ctrl.start_process(req, ui)

    def _build_header(self):
        """
        Builds the header row that displays how to information.
        """
        frame = tkb.Labelframe(self.container, text="How to")
        frame.pack(side=TOP, fill=X, padx=PAD_X, pady=PAD_Y)

        label = tkb.Label(
            frame,
            justify=CENTER,
            font=FONT,
            text="To generate tag documents, first you must gather a PLC or Kepware\n"
            + "csv file. Then select the file type you have started with. Then select\n"
            + "the document type you would like generated. Press the generate button.\n"
            + "The generated files will be exported to the reports folder.",
        )
        label.pack(pady=PAD_Y)

    def _build_file_inputs(self) -> None:
        """
        Builds the file selection widgets for the UI.
        """
        frame = tkb.Labelframe(
            self.container,
            text="Select a file.",
            padding=PAD,
        )
        frame.pack(side=TOP, fill=BOTH, padx=PAD_X, pady=PAD_Y, expand=NO)

        self._build_file_row(
            frame,
            "Input Tag List:",
            self.opt_input_file_path,
            self.input_is_selected,
            20,
            ("*.csv",),
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
        Builds the tag generator form.
        """
        self.tag_form = tkb.Labelframe(
            self.container, text="Tag Document Generator", padding=PAD
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

        Returns tuple[tkb.StringVar, tkb.Entry]
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

    def _build_text_display(self) -> None:
        """
        Builds the text display widgets for the UI.
        """
        frame = tkb.Labelframe(self.container, text="Process Output.")
        frame.pack(side=TOP, fill=BOTH, expand=YES)
        self.stext = ScrolledText(frame, height=24, font=FONT_MONO)
        self.stext.pack(side=TOP, fill=BOTH, padx=PAD_X, pady=PAD_Y, expand=YES)
        self.report.attach_text_display(self.stext)
