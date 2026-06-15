from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.app.gui import AppWindow

# stdlib
from pathlib import Path
from tkinter import ttk
from tkinter import font
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
from src.app.utils import (
    ProtocolFrame,
    PAD,
    PAD_X,
    PAD_Y,
)
from src.app.metadata import MTL_VERSION, WORKSHEET_METADATA
from src.mtl.controller import MTLController, MTLProcessorType, MTLRequest, MTLUi


class MTLFrame(ProtocolFrame):
    """
    Master controller of the MTL/CMD protocol GUI and its object variables.

    Parameters
    ----------
    parent: tkb.Frame
        The main container owned by AppWindow
    window: tkb.Window
        A back reference to the root window
    """

    def __init__(self, parent: tkb.Frame, window: AppWindow) -> None:
        super().__init__(parent)
        self.window = window
        self.proc_ctrl: MTLController = MTLController(window)
        self.stext: ScrolledText

        # TK Variables options
        self.opt_data_table = tkb.StringVar()
        self.opt_mtl_path = tkb.StringVar(value="Select a file.")
        self.opt_input_path = tkb.StringVar(value="Select a file.")
        self.opt_filter = tkb.StringVar()
        self.opt_process = tkb.IntVar(value=MTLProcessorType.NONE.value)
        self.mtl_version = tkb.StringVar(value=MTL_VERSION)
        self._mtl_is_selected = tkb.BooleanVar(value=False)
        self._input_is_selected = tkb.BooleanVar(value=False)

        # Main content frame
        self.container = ttk.Frame(self, padding=PAD)
        self.container.pack(side=TOP, fill=BOTH, expand=YES)

        self._build_file_select()
        self._build_config_options()
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
            "Select MTL/CMD:",
            self.opt_mtl_path,
            self._mtl_is_selected,
            20,
        )
        self._build_file_row(
            frame,
            "Select input CSV:",
            self.opt_input_path,
            self._input_is_selected,
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

    def _build_config_options(self) -> None:
        """
        Builds the processing configuration option widgets for the UI.
        """
        frame = tkb.Labelframe(
            self.container,
            text="Configure the WAVE processing options.",
            padding=PAD,
        )
        frame.pack(side=TOP, fill=X)

        row = ttk.Frame(frame, padding=PAD)
        row.pack(fill=X, expand=YES)

        label = tkb.Label(row, text="Filter:", padding=PAD)
        label.pack(side=LEFT, padx=PAD_X)

        entry = tkb.Entry(row, textvariable=self.opt_filter)
        entry.pack(side=LEFT, padx=PAD_X)

        cbox_label = tkb.Label(row, text="MTL/CMD Table:", padding=PAD)
        cbox_label.pack(side=LEFT, padx=PAD_X)

        self.mtl_table_cbox = tkb.Combobox(row, values=list(WORKSHEET_METADATA.keys()))
        self.mtl_table_cbox.pack(side=LEFT, fill=X, expand=YES, padx=PAD_X)
        self.mtl_table_cbox.current(0)
        self.mtl_table_cbox.bind("<<ComboboxSelected>>", self._on_mtl_table_selected)

        default_value = self.mtl_table_cbox.get()
        self.opt_data_table.set(default_value)

        version_label = tkb.Label(
            row, text=f"Compatible MTL Version: {MTL_VERSION}", padding=PAD
        )
        version_label.pack(side=RIGHT, padx=PAD_X)

    def _on_mtl_table_selected(self, event) -> None:
        """
        Gets the new table selection and sets the data_table option when its combobox
        is changed.
        """
        _ = event
        val = self.mtl_table_cbox.get()
        self.opt_data_table.set(val)

    def _build_text_display(self) -> None:
        """
        Builds the text display widgets for the UI.
        """
        frame = tkb.Labelframe(self.container, text="Process Output.")
        frame.pack(side=TOP, fill=BOTH, expand=YES)
        mono = font.nametofont("TkFixedFont")
        self.stext = ScrolledText(frame, height=24, font=mono)
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

        self.radio_append = tkb.Radiobutton(
            frame,
            text="Append",
            variable=self.opt_process,
            value=MTLProcessorType.APPEND.value,
        )
        self.radio_append.pack(side=LEFT, padx=PAD_X, pady=PAD_Y, fill=Y)

        self.radio_compare = tkb.Radiobutton(
            frame,
            text="Compare",
            variable=self.opt_process,
            value=MTLProcessorType.COMPARE.value,
        )
        self.radio_compare.pack(side=LEFT, padx=PAD_X, pady=PAD_Y, fill=Y)

        self.process_button = tkb.Button(
            frame,
            text="Process",
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
        if not (self._mtl_is_selected.get() and self._input_is_selected.get()):
            self.report.error("Please select both files to start process.")
            return

        req = MTLRequest(
            MTLProcessorType(self.opt_process.get()),
            self.opt_filter.get(),
            self.opt_data_table.get(),
            Path(self.opt_mtl_path.get()),
            Path(self.opt_input_path.get()),
        )
        ui = MTLUi(
            self.progress_bar,
            self.process_button,
            self.opt_process,
            self.stext,
        )

        self.proc_ctrl.start_process(req, ui)

    def on_teardown(self) -> None:
        """
        Called by AppWindow before the application closes.
        """
        pass
