# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH
# This tool was created with the help of AI.

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from m_wave.core.gui import App

# stdlib
import webbrowser
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
    NO,
    PRIMARY,
    READONLY,
    RIGHT,
    SUCCESS,
    TOP,
    YES,
    N,
    S,
    X,
    Y,
)
from ttkbootstrap.widgets.scrolled import ScrolledText

# local core
from m_wave.core.utils import (
    FONT_MONO,
    PAD,
    PAD_X,
    PAD_Y,
)
from m_wave.core.wavepack_frame import WavePackFrame

# local wave pack
from m_wave.wave_packs.mtl.controller import (
    MTLController,
    MTLProcessorType,
    MTLRequest,
    MTLUi,
)
from m_wave.wave_packs.mtl.extraction import DataExtractor
from m_wave.wave_packs.mtl.metadata import Metadata
from m_wave.wave_packs.mtl.paths import MTL_INSTRUCTIONS_PATH


class MTLFrame(WavePackFrame):
    """
    MTL/CMD WavePack GUI and object variables.
    """

    def __init__(self, parent: tkb.Frame, app: App) -> None:
        super().__init__(
            parent,
            height=525,
            height_min=525,
            width=850,
            width_min=850,
            resizable=(True, True),
        )
        self.app = app
        self.context = self.app.context
        self.controller: MTLController = MTLController(self.app, self.context)
        self.help_label = "MTL/CMD"

        if self.report is not None:
            self.metadata = Metadata(self.report)
        else:
            raise RuntimeError("Cannot set metadata without an initialized Report.")

        # TK Variables options
        self.opt_use_timestamps = tkb.BooleanVar(
            value=self.context.user_preferences.get("use_timestamps")
        )
        self.opt_use_msg_types = tkb.BooleanVar(
            value=self.context.user_preferences.get("use_msg_types")
        )
        self.opt_data_table = tkb.StringVar()
        self.opt_mtl_path = tkb.StringVar(value="Select a file or import from ManGo.")
        self.opt_input_path = tkb.StringVar(value="Select a file.")
        self.opt_filter = tkb.StringVar()
        self.opt_process = tkb.IntVar(value=MTLProcessorType.NONE.value)
        self.mtl_version = tkb.StringVar(value="Import needed.")
        self._mtl_is_selected = tkb.BooleanVar(value=False)
        self._input_is_selected = tkb.BooleanVar(value=False)

        # Main content frame
        self.container = ttk.Frame(self, padding=PAD)
        self.container.pack(side=TOP, fill=BOTH, expand=YES)

        self._build_file_select()
        self._build_config_options()
        self._build_process_row()
        self._build_text_display()

        self.app.after(0, self._check_for_mtl_document)

        self.report.info(
            "Welcome to the WAVE. Start the process by choosing your files.", log=False
        )
        self.report.info("For more information please use the Help Menu.", log=False)

    @property
    def report(self):
        if self.controller.report:
            return self.controller.report
        else:
            raise RuntimeError("Report not set. Cannot use WaveFrame report property")

    def get_scrolled_text(self) -> ScrolledText:
        return self.stext

    def build_menus(self, menubar: tkb.Menu) -> None:
        report_menu = tkb.Menu(menubar, tearoff=False)
        for label, var, key in (
            ("Report Timestamps", self.opt_use_timestamps, "use_timestamps"),
            ("Report Message Types", self.opt_use_msg_types, "use_msg_types"),
        ):
            report_menu.add_checkbutton(
                label=label,
                variable=var,
                command=lambda k=key, v=var: self.app._on_option_change(k, v),
            )
        menubar.add_cascade(label="Report Options", menu=report_menu)

    def _check_for_mtl_document(self) -> None:
        self.report.info("Checking files for a MTL document.")
        mtl_doc_path = self.metadata.get_mtl_document_path()
        if mtl_doc_path.exists():
            self.report.info("Found an MTL document in your files.")
            self.opt_mtl_path.set(str(mtl_doc_path))
            extractor = DataExtractor(self.report, self.metadata)
            last_rev = extractor.get_last_revision(mtl_doc_path)
            self.metadata.set_mtl_version(str(last_rev))
            self.mtl_version.set(str(last_rev))
            self.report.warning(
                f"Local MTL document is revision: {last_rev}. "
                + "If this revision is incorrect. Please use the Import button "
                + "and the app will automatically download the "
                + "latest revision.",
                popup=True,
            )
            self._mtl_is_selected.set(True)
        else:
            self.report.warning(
                "Local version of the MTL not found. "
                + "Use the Import button to automatically "
                + "download a current effective version of the MTL.",
                popup=True,
            )

    def load_mtl_instructions(self) -> str:
        try:
            with open(MTL_INSTRUCTIONS_PATH, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"Could not load MTL instructions:\n\n{e}"

    def show_help(self):
        self.report.info(
            "Instructional Video will now open.\nText instructions sent to display.",
            log=False,
            verbose=False,
            popup=True,
        )
        self.report.info(self.load_mtl_instructions(), log=False, verbose=False)
        vid_link = self.controller.configs["mtl_help_vid_url"]
        webbrowser.open(vid_link, new=1)

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

        row = tkb.Frame(frame, padding=PAD)
        row.pack(fill=X)
        import_button = tkb.Button(
            row,
            text="Import",
            bootstyle=PRIMARY,
            padding=PAD,
            width=15 - int(PAD / 1.5),
            command=self._on_import_clicked,
        )
        import_button.pack(side=RIGHT)
        pick_button = tkb.Button(
            row,
            text="Pick File",
            bootstyle=PRIMARY,
            padding=PAD,
            width=15 - int(PAD / 1.5),
            command=lambda: self._set_filepath(
                self.opt_mtl_path,
                self._mtl_is_selected,
                (".xlsx",),
            ),
        )
        pick_button.pack(side=RIGHT, padx=(0, PAD_X * 2.3))

        label = tkb.Label(
            row,
            text="Select your MTL Excel Document:",
            padding=PAD,
            width=30,
        )
        label.pack(side=LEFT)
        entry = tkb.Entry(row, textvariable=self.opt_mtl_path, state=READONLY)
        entry.pack(side=LEFT, fill=BOTH, expand=YES, padx=PAD_X)

        self._build_file_row(
            frame,
            "Select your Pi Builder export CSV:",
            self.opt_input_path,
            self._input_is_selected,
            30,
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
        entry = tkb.Entry(row, textvariable=path_variable, state=READONLY)
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
            print(file_path)
            file_path = file_path.replace("/", "\\")
            print(file_path)
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

        keys = list(self.metadata.worksheet_metadata.keys())
        self.mtl_table_cbox = tkb.Combobox(row, values=keys)
        self.mtl_table_cbox.pack(side=LEFT, fill=X, expand=YES, padx=PAD_X)
        self.mtl_table_cbox.current(0)
        self.mtl_table_cbox.bind("<<ComboboxSelected>>", self._on_mtl_table_selected)

        default_value = self.mtl_table_cbox.get()
        self.opt_data_table.set(default_value)

        self.version_entry = tkb.Entry(
            row,
            textvariable=self.mtl_version,
        )
        self.version_entry.pack(side=RIGHT, padx=PAD_X)

        version_key_label = tkb.Label(
            row,
            text="MTL Revision:",
            padding=PAD,
        )
        version_key_label.pack(side=RIGHT, padx=PAD_X)

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

    def _on_import_clicked(self) -> None:
        """
        Attempts to import the MTL on button clicked. Builds a request and passes ui
        objects to the process thread.
        """

        req = MTLRequest(
            MTLProcessorType(MTLProcessorType.DOWNLOAD.value),
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
            self.mtl_version,
            self.opt_mtl_path,
        )

        self.controller.start_process(req, ui)
        self._mtl_is_selected.set(True)

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
            self.mtl_version,
            self.opt_mtl_path,
        )

        self.controller.start_process(req, ui)
