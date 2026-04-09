# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
#
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH

# stdlib
import logging
import threading
import json
from datetime import datetime
from enum import Enum
from tkinter.filedialog import askopenfilename as open_file

# third party
import ttkbootstrap as ttk
from ttkbootstrap.constants import (
    BOTH,
    NORMAL,
    DISABLED,
    X,
    Y,
    LEFT,
    RIGHT,
    BOTTOM,
    TOP,
    YES,
    N,
    S,
    PRIMARY,
    SECONDARY,
    SUCCESS,
    INDETERMINATE,
)

# local
from src.metadata import DATETIME_FORMAT, MTL_VERSION, WORKSHEET_METADATA
from src.paths import ASSETS_DIR, CONFIG_PATH, LOGS_DIR, REPORTS_DIR, INSTRUCTIONS_PATH
from src.process import Process
from src.reporting import Reporting

# Logging initialization
FORMAT = "%(asctime)s:%(levelname)s:%(filename)s:%(name)s::%(message)s"
# FIX: Move this to metadata
LOGO_PATH = ASSETS_DIR / "logo.png"
# FIX: END
LOG_DATETIME = datetime.now().strftime(DATETIME_FORMAT)
LOG_FILENAME = LOGS_DIR / f"{LOG_DATETIME}_general_error.log"

# CONSTANTS
THEMES = ("cosmo", "flatly", "litera", "superhero", "darkly", "vapor")
FRAME_PADDING = 16
ROW_PADDING = 8
APP_SIZE = (920, 460)
APP_MINSIZE = (920, 460)

with open(INSTRUCTIONS_PATH, "r", encoding="utf-8") as f:
    INSTRUCTIONS = f.read()


logger = logging.getLogger(__name__)
logging.basicConfig(
    filename=LOG_FILENAME,
    filemode="w",
    format=FORMAT,
    encoding="utf-8",
    level=logging.DEBUG,
)


class ProcessType(int, Enum):
    NONE = 0
    COMPARE = 1
    APPEND = 2


class App:
    """
    A MTL/CMD format helper process. This program takes in file path information
    from the user and uses it to either format new Aveva PI tag and configuration
    context information into or compare and validate data between csv input data
    against design document 20471406.
    """

    def __init__(self) -> None:
        config = self._load_user_configs()

        # Initialize the root ttk window and options
        self.window = ttk.Window(
            title="λ Workbook Automation & Verification Engine",
            themename=config.get("theme", "litera"),
            size=APP_SIZE,
            minsize=APP_MINSIZE,
        )
        self.style = ttk.Style()
        self.icon = ttk.PhotoImage(file=str(LOGO_PATH))
        self.window.iconphoto(False, self.icon)

        # Init Reporting
        self.report = Reporting(
            self.window, REPORTS_DIR, use_timestamps=False, use_msg_types=False
        )

        # Init ttk variables
        self.selected_theme = ttk.StringVar(value=config.get("theme", "litera"))
        self.use_timestamps = ttk.BooleanVar(value=config.get("use_timestamps", False))
        self.use_msg_types = ttk.BooleanVar(value=config.get("use_msg_types", False))

        ## Strings
        self.selected_data_table = ttk.StringVar()
        self.mtl_version = ttk.StringVar(value=MTL_VERSION)
        self.input_file_path = ttk.StringVar(value="Select a file.")
        self.mtl_file_path = ttk.StringVar(value="Select a file.")
        self.filter_string = ttk.StringVar(value="")

        ## Ints
        self.selected_process = ttk.IntVar(value=ProcessType.NONE.value)

        ## Booleans
        self.input_selected = ttk.BooleanVar(value=False)
        self.mtl_selected = ttk.BooleanVar(value=False)

        # Init other app variables
        self.process_thread = None
        self.worksheets = {
            name: table_id for name, table_id in WORKSHEET_METADATA.items()
        }

        # Debug gui setup - Remove?
        # self.debug_style = ttk.Style()
        # self.debug_style.configure("Debug.TFrame", background="white")

        # Initialize ttkboostrap frames and widgets
        self.setup_menus()
        self.create_main_content_frame()
        self.create_file_select_frame()
        self.create_option_frame()
        self.create_footer_frame()

    def _load_user_configs(self) -> dict:
        """
        Tries to load the user configurations and returns a dict of settings.
        """
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            try:
                cfg = json.load(f)
                return cfg
            except json.JSONDecodeError as e:
                raise json.JSONDecodeError(
                    f"Failed to parse config file at: 'CONFIG_PATH': {e.msg}",
                    e.doc,
                    e.pos,
                )
            except Exception as e:
                raise RuntimeError(
                    f"An unexpected error occurred during loading the configuration.\n{e}"
                )

    def _update_config(self, key, value) -> None:
        """
        Updates the user configuration for theme, time stamps, and message types.
        """
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        cfg[key] = value

        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)

    def _update_report(self) -> None:
        """
        Sets a new report by re-initializing the self.report variable.
        """
        if self.process_thread and self.process_thread.is_alive():
            self.use_timestamps.set(self.report.use_timestamps)
            self.use_msg_types.set(self.report.use_msg_types)
            self.report.error(
                "Cannot update reporting settings while a process is running",
                popup=True,
            )
            return

        self.report = Reporting(
            self.window,
            REPORTS_DIR,
            use_timestamps=self.use_timestamps.get(),
            use_msg_types=self.use_msg_types.get(),
        )

        self._update_config("use_timestamps", self.use_timestamps.get())
        self._update_config("use_msg_types", self.use_msg_types.get())

        self.report.debug("Report options changed: ", report=False)
        self.report.debug(
            f"Use Timestamps is: {self.use_timestamps.get()}", report=False
        )
        self.report.debug(
            f"Use Message Types is: {self.use_msg_types.get()}", report=False
        )

    def _on_theme_select(self, theme: str) -> None:
        """
        Changes variables and theme, on theme selected/changed.
        """
        self.selected_theme.set(theme)
        self.style.theme_use(theme)
        self._update_config("theme", self.selected_theme.get())
        self.report.debug(f"Theme changed: {theme}", report=False)

    def setup_menus(self):
        """
        Setup the header menus.
        """
        self.menubar = ttk.Menu(self.window)

        # Simple file menu
        self.file_menu = ttk.Menu(self.menubar, tearoff=0)
        self.file_menu.add_command(label="Exit", command=self.window.destroy)

        self.menubar.add_cascade(label="File", menu=self.file_menu)

        # Report option menu that changes reporting options.
        self.option_menu = ttk.Menu(self.menubar, tearoff=0)
        self.option_menu.add_checkbutton(
            label="Add timestamps to the report",
            variable=self.use_timestamps,
            command=self._update_report,
        )
        self.option_menu.add_checkbutton(
            label="Add message types to the report",
            variable=self.use_msg_types,
            command=self._update_report,
        )
        self.menubar.add_cascade(label="Report Options", menu=self.option_menu)

        # Simple fun menu that changes the app theme.
        self.theme_menu = ttk.Menu(self.menubar, tearoff=0)
        for theme in THEMES:
            self.theme_menu.add_radiobutton(
                label=theme.capitalize(),
                value=theme,
                variable=self.selected_theme,
                command=lambda t=theme: self._on_theme_select(t),
            )

        self.menubar.add_cascade(label="Themes", menu=self.theme_menu)

        # Help menu that will display usage instructions.
        self.help_menu = ttk.Menu(self.menubar, tearoff=0)
        self.help_menu.add_command(
            label="Instructions",
            command=lambda: self.report.info(
                INSTRUCTIONS, log=False, verbose=False, popup=True
            ),
        )

        self.menubar.add_cascade(label="Help", menu=self.help_menu)

        self.window.config(menu=self.menubar)

    def get_filepath(
        self,
        string_variable: ttk.StringVar,
        is_selected: ttk.BooleanVar,
        file_types: list[tuple] | None = None,
    ) -> None:
        """
        Use file_dialog to get a file path and set it to a ttk variable.
        file_types = [('Key', ('*.type',))]
        Returns a boolean to set if selection was successful
        """
        if file_types is None:
            file_types = [
                ("Supported files", ("*.xlsx", "*.xlsm")),
            ]

        user_input = open_file(title="Select a file", filetypes=file_types)

        if user_input:
            string_variable.set(user_input)
            is_selected.set(True)
        else:
            string_variable.set("File selection canceled!")
            is_selected.set(False)

    def create_main_content_frame(self) -> None:
        """
        Creates and formats the app's main work space using a frame.
        """
        self.content_frame = ttk.Frame(self.window, padding=15)
        self.content_frame.pack(fill=BOTH, expand=YES)

    def create_file_select_frame(self) -> None:
        """
        Creates and formats a label frame for collecting the file paths from
        the user.
        """
        frame = ttk.Labelframe(
            self.content_frame,
            text="Select the working files",
            padding=15,
        )
        frame.pack(side=TOP, anchor=N, fill=BOTH)

        # Create and format the file path collection widgets for the mtl/cmd.
        mtl_row = ttk.Frame(frame, padding=10)
        mtl_row.pack(fill=X, expand=YES)
        mtl_label = ttk.Label(mtl_row, text="MTL/CMD File:", padding=10, width=20)
        mtl_label.pack(side=LEFT)
        mtl_entry = ttk.Entry(mtl_row, textvariable=self.mtl_file_path)
        mtl_entry.pack(side=LEFT, fill=X, expand=YES, padx=10)
        mtl_button = ttk.Button(
            mtl_row,
            text="Pick file",
            bootstyle=PRIMARY,
            padding=10,
            width=20,
            command=lambda: self.get_filepath(self.mtl_file_path, self.mtl_selected),
        )
        mtl_button.pack(side=RIGHT)

        # Create and format the file path collection widgets for input data
        input_row = ttk.Frame(frame, padding=10)
        input_row.pack(fill=X, expand=YES)
        input_label = ttk.Label(input_row, text="Input File:", padding=10, width=20)
        input_label.pack(side=LEFT)
        input_entry = ttk.Entry(input_row, textvariable=self.input_file_path)
        input_entry.pack(side=LEFT, fill=X, expand=YES, padx=10)
        input_button = ttk.Button(
            input_row,
            text="Pick file",
            bootstyle=SECONDARY,
            padding=10,
            width=20,
            command=lambda: self.get_filepath(
                self.input_file_path,
                self.input_selected,
                [("Supported files", ("*.csv",))],
            ),
        )
        input_button.pack(side=RIGHT)

    def _on_combobox_select(self, event=None):
        """
        Determines functionality when the type option combo box changes.
        """
        selected_value = self.mtl_table_cbox.get()
        self.selected_data_table.set(selected_value)
        self.report.debug(f"Selected: {selected_value}", report=False)

    def create_option_frame(self) -> None:
        """
        Creates and formats the app's options frame.
        """
        frame = ttk.Labelframe(
            self.content_frame,
            text="Configure the WAVE-MCR processing options.",
            padding=15,
        )
        frame.pack(side=TOP, anchor=N, fill=BOTH, pady=8)
        opt_row = ttk.Frame(frame, padding=10)
        opt_row.pack(fill=X, expand=YES)

        # Create the entry widget that filters data to an object name.
        filter_label = ttk.Label(opt_row, text="Filter:", padding=10)
        filter_label.pack(side=LEFT, padx=10)
        filter_entry = ttk.Entry(opt_row, textvariable=self.filter_string)
        filter_entry.pack(side=LEFT, padx=10)
        self.report.debug(f"Default name filter: {filter_entry.get()}", report=False)

        # Create the combo box widget for selecting the MTL/CMD data table.
        cbox_label = ttk.Label(
            opt_row,
            text="MTL/CMD Table:",
            padding=10,
        )
        cbox_label.pack(side=LEFT, padx=10)
        self.cbox_options = list(self.worksheets.keys())
        self.mtl_table_cbox = ttk.Combobox(
            opt_row,
            values=self.cbox_options,
        )
        self.mtl_table_cbox.pack(side=LEFT, fill=X, expand=YES, padx=10)
        self.mtl_table_cbox.current(0)
        self.mtl_table_cbox.bind("<<ComboboxSelected>>", self._on_combobox_select)
        default_value = self.mtl_table_cbox.get()
        self.selected_data_table.set(default_value)
        self.report.debug(
            f"Default MTL/CMD Table Selected: {default_value}", report=False
        )

        # Create the label widget that displays the compatible MTL/CMD version.
        version_label = ttk.Label(
            opt_row,
            text=f"Compatible MTL Version: {self.mtl_version.get()}",
            padding=10,
        )
        version_label.pack(side=RIGHT, padx=10)

    def _process_handler(self) -> None:
        """
        Run the data transfer/comparison process.
        """

        selected_process = ProcessType(self.selected_process.get())
        if selected_process == ProcessType.NONE:
            self.window.after(
                0,
                lambda: self.report.error(
                    "Please select Compare or Append.", popup=True
                ),
            )
            return

        # Validate file paths
        if not self.mtl_selected.get() or not self.input_selected.get():
            self.report.error("Please select both input files.", popup=True)
            return

        # Check if process is in progress
        if self.process_thread and self.process_thread.is_alive():
            self.report.warning("Process already running!", popup=True)
            return

        self.process_button.config(state=DISABLED)
        self.progress_bar.start()

        def subroutine():
            """
            Threaded data processing daemon target.
            Handles report creation and input processing.
            """
            self.report.debug("Starting subroutine...", report=False)
            try:
                new_report_name = self.filter_string.get() or "Unfiltered"
                self.report.create_report(new_report_name)
                self.report.debug(
                    f"Report name should be: {new_report_name}", report=False
                )
                process = Process(
                    self.report,
                    self.filter_string.get(),
                    self.selected_data_table.get(),
                    self.mtl_file_path.get(),
                    self.input_file_path.get(),
                )
                if selected_process == ProcessType.APPEND:
                    self.report.debug("Appending data...", report=False)
                    process.append_input()
                else:
                    self.report.debug("Comparing supplied data...", report=False)
                    process.compare_input()
            except Exception as e:
                self.report.exception(f"Subroutine process error:\n{e}", popup=True)
            finally:
                self.window.after(
                    0, lambda: self.report.info("Subroutine Completed.", popup=True)
                )
                self.window.after(0, self.progress_bar.stop)
                self.window.after(
                    0, lambda: self.selected_process.set(ProcessType.NONE.value)
                )
                self.window.after(0, lambda: self.process_button.config(state=NORMAL))

        self.process_thread = threading.Thread(target=subroutine, daemon=True)
        self.process_thread.start()

    def create_footer_frame(self) -> None:
        """
        Creates a footer frame that contains the process selection and activity widgets.
        """
        row = ttk.Frame(self.content_frame, padding=15)
        row.pack(fill=BOTH, side=BOTTOM, anchor=S)

        self.progress_bar = ttk.Progressbar(row, mode=INDETERMINATE)
        self.progress_bar.pack(side=LEFT, expand=YES, padx=15, fill=X)

        self.process_button = ttk.Button(
            row,
            text="Process",
            bootstyle=SUCCESS,
            padding=10,
            width=20,
            command=lambda: self._process_handler(),
        )
        self.process_button.pack(side=RIGHT, padx=10, fill=Y)

        self.rb_append = ttk.Radiobutton(
            row,
            text="Append",
            variable=self.selected_process,
            value=ProcessType.APPEND.value,
        )
        self.rb_append.pack(side=RIGHT, padx=10, fill=Y)

        self.rb_compare = ttk.Radiobutton(
            row,
            text="Compare",
            variable=self.selected_process,
            value=ProcessType.COMPARE.value,
        )
        self.rb_compare.pack(side=RIGHT, padx=10, fill=Y)

    def run(self) -> None:
        """
        Runs the main process.
        """
        self.window.mainloop()


if __name__ == "__main__":
    app = App()
    app.run()
