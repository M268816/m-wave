# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
#
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH

"""
The GUI classe within this module is used to control the display of the application.

Classes
-------
Gui
    Master controller of the GUI and object variables.
"""

# stdlib
from pathlib import Path
from tkinter import ttk
from tkinter import font
from tkinter.filedialog import askopenfilename
from tkinter.scrolledtext import ScrolledText

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

# local
from src.metadata import MTL_VERSION, WORKSHEET_METADATA
from src.paths import LOGO_PATH, INSTRUCTIONS_PATH
from src.controller import Controller, ProcessRequest, ProcessType, ProcessUi

# CONSTANTS
APP_SIZE = (850, 525)
APP_MINSIZE = (850, 525)
PAD_X = 8
PAD_Y = 8
PAD = 8
THEMES = (
    "cosmo",
    "flatly",
    "journal",
    "litera",
    "lumen",
    "minty",
    "pulse",
    "sandstone",
    "united",
    "yeti",
    "morph",
    "simplex",
    "cerculean",
    "solar",
    "superhero",
    "darkly",
    "cyborg",
    "vapor",
)

with open(INSTRUCTIONS_PATH, "r", encoding="utf-8") as f:
    INSTRUCTIONS = f.read()


class Gui:
    """
    Master controller of the GUI and object variables.

    Attributes
    ----------
    window: tkb.Window
        a root window used to display the application
    app_size: tuple[int,int]
        the starting size of the application (width,height)
    app_minsize: tuple[int,int]
        the minimum size of the application (width,height)

    Methods
    -------
    set_config_value(key, value)
        writes a single configuration value to the json file.

    reset_report(text_display, filter_value)
        Sets/creates a new report by re-initializing

    start_process(req, ui)
        Starts the data processing functions.
    """

    def __init__(
        self,
        window: tkb.Window,
        app_size: tuple[int, int] = APP_SIZE,
        app_minsize: tuple[int, int] = APP_MINSIZE,
    ) -> None:
        self.root = window
        self.stext = ScrolledText()
        self.controller = Controller(self.root)
        self.style = tkb.Style()

        self.root.geometry(f"{app_size[0]}x{app_size[1]}")
        self.root.minsize(app_minsize[0], app_minsize[1])
        self.logo = tkb.PhotoImage(file=str(LOGO_PATH))
        self.root.iconphoto(False, self.logo)

        # User options
        self.opt_theme = tkb.StringVar(
            value=self.controller.user_configs.get("theme", "litera")
        )
        self.opt_timestamps = tkb.BooleanVar(
            value=self.controller.user_configs.get("use_timestamps", False)
        )
        self.opt_msg_types = tkb.BooleanVar(
            value=self.controller.user_configs.get("use_msg_types", False)
        )
        self.opt_data_table = tkb.StringVar()
        self.opt_mtl_path = tkb.StringVar(value="Select a file.")
        self.opt_input_path = tkb.StringVar(value="Select a file.")
        self.opt_filter = tkb.StringVar()
        self.opt_process = tkb.IntVar(value=ProcessType.NONE.value)
        self.style.theme_use(self.opt_theme.get())

        # Other variables
        self.mtl_version = tkb.StringVar(value=MTL_VERSION)
        self._mtl_is_selected = tkb.BooleanVar(value=False)
        self._input_is_selected = tkb.BooleanVar(value=False)

        # Main content frame
        self.content = ttk.Frame(self.root, padding=PAD)
        self.content.pack(side=TOP, fill=BOTH, expand=YES)

        self._build_menu()
        self._build_file_select()
        self._build_config_options()
        self._build_text_display()
        self._build_process_row()

        self.controller.report.info(
            "Welcome to the WAVE. Start the process by choosing your files.", log=False
        )
        self.controller.report.info(
            "For more information please use the Help Menu.", log=False
        )

    def _build_menu(self) -> None:
        """
        Builds the header menus for the UI.
        """
        menubar = tkb.Menu(self.content)

        file_menu = tkb.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Exit", command=self.root.destroy)
        menubar.add_cascade(label="File", menu=file_menu)

        option_menu = tkb.Menu(menubar, tearoff=0)
        option_menu.add_checkbutton(
            label="Add time stamps to reports.",
            variable=self.opt_timestamps,
            command=lambda: self._on_option_change(
                "use_timestamps", self.opt_timestamps
            ),
        )
        option_menu.add_checkbutton(
            label="Add message types to reports.",
            variable=self.opt_msg_types,
            command=lambda: self._on_option_change("use_msg_types", self.opt_msg_types),
        )
        menubar.add_cascade(label="Report Options", menu=option_menu)

        theme_menu = tkb.Menu(menubar, tearoff=0)
        for theme in THEMES:
            theme_menu.add_radiobutton(
                label=theme.capitalize(),
                value=theme,
                variable=self.opt_theme,
                command=lambda t=tkb.StringVar(None, theme): self._on_theme_change(t),
            )
        menubar.add_cascade(label="Themes", menu=theme_menu)

        help_menu = tkb.Menu(menubar, tearoff=0)
        help_menu.add_command(
            label="Instructions",
            command=lambda: (
                self.controller.report.info(
                    "Instructions pushed to text display.",
                    log=False,
                    verbose=False,
                    popup=True,
                ),
                self.controller.report.info(
                    INSTRUCTIONS,
                    log=False,
                    verbose=False,
                ),
            ),
        )
        menubar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menubar)

    def _on_theme_change(self, theme: tkb.StringVar) -> None:
        """
        Changes the variables and theme when the theme is changed.
        """
        self.style.theme_use(theme.get())
        self.controller.set_config_value("theme", theme)

    def _on_option_change(self, config_key: str, var: tkb.BooleanVar) -> None:
        """
        On report option change, updates the configuration and resets the report.
        """
        self.controller.set_config_value(config_key, var)

    def _build_file_select(self) -> None:
        """
        Builds the file selection widgets for the UI.
        """
        frame = tkb.Labelframe(
            self.content,
            text="Select your files.",
            padding=PAD,
        )
        frame.pack(side=TOP, anchor=N, fill=X, expand=NO)

        self._build_data_row(
            frame,
            "Select MTL/CMD:",
            self.opt_mtl_path,
            self._mtl_is_selected,
            20,
        )
        self._build_data_row(
            frame,
            "Select input CSV:",
            self.opt_input_path,
            self._input_is_selected,
            20,
            ("*.csv",),
        )

    def _build_data_row(
        self,
        frame: tkb.Labelframe,
        label_text: str,
        path_variable: tkb.StringVar,
        is_selected: tkb.BooleanVar,
        width: int,
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
            self.content,
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
        frame = tkb.Labelframe(self.content, text="Process Output.")
        frame.pack(side=TOP, fill=BOTH, expand=YES)
        frame.pack_propagate(False)
        mono = font.nametofont("TkFixedFont")
        self.stext = ScrolledText(frame, height=24)
        self.stext.configure(font=mono)
        self.stext.pack(side=TOP, fill=BOTH, padx=PAD_X, pady=PAD_Y, expand=YES)
        self.controller.report.attach_text_display(self.stext)

    def _build_process_row(self) -> None:
        """
        Builds the footer row that holds the processing options and progress bar
        indicator.
        """
        frame = tkb.Labelframe(self.content, text="Process Status")
        frame.pack(side=BOTTOM, fill=X, anchor=S)

        self.progress_bar = tkb.Progressbar(frame, mode=INDETERMINATE)
        self.progress_bar.pack(side=LEFT, expand=YES, padx=PAD_X, pady=PAD_Y, fill=X)

        self.radio_append = tkb.Radiobutton(
            frame,
            text="Append",
            variable=self.opt_process,
            value=ProcessType.APPEND.value,
        )
        self.radio_append.pack(side=LEFT, padx=PAD_X, pady=PAD_Y, fill=Y)

        self.radio_compare = tkb.Radiobutton(
            frame,
            text="Compare",
            variable=self.opt_process,
            value=ProcessType.COMPARE.value,
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
            self.controller.report.error("Please select both files to start process.")
            return

        req = ProcessRequest(
            ProcessType(self.opt_process.get()),
            self.opt_filter.get(),
            self.opt_data_table.get(),
            Path(self.opt_mtl_path.get()),
            Path(self.opt_input_path.get()),
        )
        ui = ProcessUi(
            self.progress_bar,
            self.process_button,
            self.opt_process,
            self.stext,
        )

        self.controller.start_process(req, ui)

    def run(self) -> None:
        """
        Run the main tk application loop.
        """
        self.root.mainloop()


if __name__ == "__main__":
    window = tkb.Window(title="Testing")
    test = Gui(window)
    test.run()
