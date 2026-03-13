# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
#
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH

import logging
import threading
import ttkbootstrap as ttk
from datetime import datetime
from pathlib import Path
from src.process import Process
from src.reporting import Reporting
from tkinter.filedialog import askopenfilename as open_file
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

# Logging initialization
FORMAT = "%(asctime)s:%(levelname)s:%(filename)s:%(name)s::%(message)s"
DATETIME_FORMAT = "%Y-%m-%dT%H_%M_%S-%f"
OUTPUT_DIR = "logs"
LOG_DATETIME = datetime.now().strftime(DATETIME_FORMAT)
LOG_FILENAME = f"{str(Path(OUTPUT_DIR))}/{LOG_DATETIME}_general.log"

Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

logger = logging.getLogger(__name__)
logging.basicConfig(
    filename=LOG_FILENAME,
    filemode="w",
    format=FORMAT,
    encoding="utf-8",
    level=logging.DEBUG,
)

# The current version of the MTL this application is built for
MTL_VERSION = "20.0"


class App:
    """
    A MTL/CMD format helper process. This program takes in file path information
    from the user and uses it to either format new Aveva PI tag and configuration
    context information into or compare and validate data between csv input data
    aginst design document 20471406.
    """

    def __init__(self) -> None:
        # Initialize the root ttk window
        self.window = ttk.Window(
            title="λ Workbook Automation & Verification Engine (WAVE)",
            themename="superhero",
            size=(1280, 720),
            minsize=(1175, 450),
        )
        self.report = Reporting(
            "main", output_dir=OUTPUT_DIR, parent_window=self.window
        )
        self.report.title("TK INITIALIZATION")
        self.report.debug("App starting...", log_only=True)
        self.report.debug("GUI window created.", log_only=True)
        # Init ttk variables
        self.selected_data_table = ttk.StringVar()
        self.name_filter = ttk.StringVar(value=None)
        self.mtl_version = ttk.StringVar(value=MTL_VERSION)
        self.input_data_file_path = ttk.StringVar(value="Select a file.")
        self.mtl_file_path = ttk.StringVar(value="Select a file.")
        self.report.debug("TTK object variables created.", log_only=True)
        # Init other app variables
        self.process = Process()
        self.process_thread = None
        self.worksheet_metadata = self.process.worksheet_metadata
        self.report.debug("App variables created.", log_only=True)
        # Debug gui setup
        self.debug_style = ttk.Style()
        self.debug_style.configure("Debug.TFrame", background="white")
        # Initialize ttkboostrap frames and widgets
        self.create_main_content_frame()
        self.create_file_select_frame()
        self.create_option_frame()
        self.create_footer_frame()
        self.report.debug("Frames and widgets created.", log_only=True)

    def get_filepath(
        self, string_variable: ttk.StringVar, file_types: list[tuple] | None = None
    ) -> None:
        """
        Use file_dialog to get a file path and set it to a ttk variable.
        file_types = [('Key', ('*.type',))]
        """
        if file_types is None:
            file_types = [
                ("Supported files", ("*.xlsx", "*.xlsm")),
            ]
        user_input = open_file(title="Select a file", filetypes=file_types)
        if user_input:
            string_variable.set(user_input)
        else:
            string_variable.set("File selection canceled!")

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
            command=lambda: self.get_filepath(self.mtl_file_path),
        )
        mtl_button.pack(side=RIGHT)

        # Create and format the file path collection widgets for input data
        input_row = ttk.Frame(frame, padding=10)
        input_row.pack(fill=X, expand=YES)
        input_label = ttk.Label(input_row, text="Input File:", padding=10, width=20)
        input_label.pack(side=LEFT)
        input_entry = ttk.Entry(input_row, textvariable=self.input_data_file_path)
        input_entry.pack(side=LEFT, fill=X, expand=YES, padx=10)
        input_button = ttk.Button(
            input_row,
            text="Pick file",
            bootstyle=SECONDARY,
            padding=10,
            width=20,
            command=lambda: self.get_filepath(
                self.input_data_file_path, [("Supported files", ("*.csv"))]
            ),
        )
        input_button.pack(side=RIGHT)

    def on_combobox_select(self, event):
        """
        Determines functionality when the type option combo box changes.
        """
        selected_value = self.mtl_table_cbox.get()
        self.selected_data_table.set(selected_value)
        self.report.debug(f"Selected: {selected_value}", log_only=True)

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
        name_label = ttk.Label(opt_row, text="Object Name:", padding=10)
        name_label.pack(side=LEFT, padx=10)
        name_entry = ttk.Entry(opt_row, textvariable=self.name_filter)
        name_entry.pack(side=LEFT, padx=10)
        self.report.debug(f"Default name filter: {name_entry.get()}", log_only=True)

        # Create the combo box widget for selecting the MTL/CMD data table.
        cbox_label = ttk.Label(
            opt_row,
            text="MTL/CMD Table:",
            padding=10,
        )
        cbox_label.pack(side=LEFT, padx=10)
        self.cbox_options = list(self.worksheet_metadata.keys())
        self.mtl_table_cbox = ttk.Combobox(
            opt_row,
            values=self.cbox_options,
        )
        self.mtl_table_cbox.pack(side=LEFT, fill=X, expand=YES, padx=10)
        self.mtl_table_cbox.current(0)
        self.mtl_table_cbox.bind("<<ComboboxSelected>>", self.on_combobox_select)
        default_value = self.mtl_table_cbox.get()
        self.selected_data_table.set(default_value)
        self.report.debug(
            f"Default MTL/CMD Table Selected: {default_value}", log_only=True
        )

        # Create the label widget that displays the compatable MTL/CMD version.
        version_label = ttk.Label(
            opt_row,
            text=f"Required MTL/CMD Version: {self.mtl_version.get()}",
            padding=10,
        )
        version_label.pack(side=RIGHT, padx=10)

    def _process_handler(self, is_appending: bool = False) -> None:
        """
        Run the data transfer/validate process.
        """
        # Validate file paths
        if (
            self.mtl_file_path.get() == "Select a file."
            or self.input_data_file_path.get() == "Select a file."
            or self.mtl_file_path.get() == "File selection canceled!"
            or self.input_data_file_path.get() == "File selection canceled!"
        ):
            self.report.error("Please select both input files.", popup=True)
            return
        if self.process_thread and self.process_thread.is_alive():
            self.report.warning("Process already running!", popup=True)
            return

        self.validate_btn.config(state=DISABLED)
        self.progress_bar.start()

        def subroutine():
            """
            Pushes the process of loading the information to input to another
            thread.
            """
            self.report.debug("Starting subroutine...", log_only=True)
            try:
                report_name = self.name_filter.get() or "Full_Test"
                self.report.debug(f"Report name should be: {report_name}")
                self.process.rename_report(report_name)
                if is_appending:
                    self.report.debug("Appending data...")
                    self.process.append()
                else:
                    self.report.debug("Validating comparison data...")
                    self.process.validate(
                        self.name_filter.get(),
                        self.input_data_file_path.get(),
                        self.mtl_file_path.get(),
                        self.selected_data_table.get(),
                    )
                self.window.after(
                    0, lambda: self.report.debug("Subroutine Completed.", popup=True)
                )
            except Exception as e:
                self.report.exception(f"Subroutine process error:\n{e}", popup=True)
            finally:
                self.window.after(0, self.progress_bar.stop)
                self.window.after(0, lambda: self.validate_btn.config(state=NORMAL))

        self.process_thread = threading.Thread(target=subroutine, daemon=True)
        self.process_thread.start()

    def create_footer_frame(self) -> None:
        """
        Creates the row to manage the bottom submit/cancel buttons.
        """
        row = ttk.Frame(self.content_frame, padding=15)
        row.pack(fill=BOTH, side=BOTTOM, anchor=S)
        self.progress_bar = ttk.Progressbar(row, mode=INDETERMINATE)
        self.progress_bar.pack(side=LEFT, expand=YES, padx=15, fill=X)
        self.validate_btn = ttk.Button(
            row,
            text="Validate",
            bootstyle=SUCCESS,
            padding=10,
            width=20,
            command=lambda: self._process_handler(),
        )
        self.append_btn = ttk.Button(
            row,
            text="Append",
            padding=10,
            width=25,
            command=lambda: self._process_handler(is_appending=True),
            state=DISABLED,
        )
        self.validate_btn.pack(side=RIGHT, padx=10, fill=Y)
        self.append_btn.pack(side=RIGHT, padx=15, fill=Y)
        row.configure()

    def run(self) -> None:
        """
        Runs the main process.
        """
        self.window.mainloop()


if __name__ == "__main__":
    app = App()
    app.run()
