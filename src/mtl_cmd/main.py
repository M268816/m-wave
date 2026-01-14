# Copyriggt 2022 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
#
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH

from openpyxl import load_workbook
from tkinter.filedialog import askopenfilename as file_dialog
from ttkbootstrap.constants import (
    BOTH,
    X,
    Y,
    LEFT,
    RIGHT,
    BOTTOM,
    TOP,
    YES,
    N,
    E,
    S,
    W,
    HORIZONTAL,
    VERTICAL,
    PRIMARY,
    SECONDARY,
    SUCCESS,
    HEADINGS,
    DETERMINATE,
    INDETERMINATE,
)
import pandas as pd
import threading
import ttkbootstrap as ttk


class App:
    """
    A MTL/CMD format helper process. This program takes in file path information
    from the user that it uses to format new Aveva PI tag and configuration
    context information into design document 20471406.
    """

    def __init__(self) -> None:
        """
        This app uses ttkbootstrap for the gui and pandas for data
        processing.
        """
        # initialize root ttk window
        self.window = ttk.Window(
            title="Master Tag List / Context Master Data format helper.",
            themename="superhero",
            size=(640, 360),
            minsize=(640, 360),
        )
        # init ttk variables
        self.selected_data_type = ttk.StringVar()
        self.selected_data_env = ttk.StringVar()
        self.selected_mtl_version = ttk.StringVar(value="19.0")
        self.input_data_file_path = ttk.StringVar(value="Select a file.")
        self.mtl_file_path = ttk.StringVar(value="Select a file.")
        # gui debug
        self.debug_style = ttk.Style()
        self.debug_style.configure("Debug.TFrame", background="white")
        # initialize ttk frames and widgets
        self.create_content_frame()
        self.create_file_selection_frame()
        self.create_preview_table_frame()
        self.create_footer_frame()
        # TODO: Process the data.
        # TODO: Threading
        # TODO: Progress Bar
        # TODO: Logging and view log button

    def create_content_frame(self) -> None:
        """
        Creates and formats the app's main workspace using a frame.
        """
        self.content_frame = ttk.Frame(self.window, padding=15)
        self.content_frame.pack(fill=BOTH, expand=YES)

    def get_filepath(self, string_variable: ttk.StringVar) -> None:
        """
        Use file_dialog to get a file path and set it to a ttk variable.
        """
        file_types = [
            ("Supported files", ("*.xlsx", "*.xlsm")),
        ]
        user_input = file_dialog(title="Select a file", filetypes=file_types)
        if user_input:
            string_variable.set(user_input)
        else:
            string_variable.set("File selection canceled!")

    def create_mtl_file_frame(self, parent: ttk.Labelframe) -> None:
        """
        Creates the formats the file path collection widgets for the mtl/cmd
        file.
        """
        row = ttk.Frame(parent, padding=10)
        label = ttk.Label(
            row,
            text="MTL/CMD File:",
            padding=10,
        )
        entry = ttk.Entry(row, textvariable=self.mtl_file_path)
        button = ttk.Button(
            row,
            text="Pick file",
            bootstyle=PRIMARY,
            padding=10,
            width=20,
            command=lambda: self.get_filepath(self.mtl_file_path),
        )
        row.pack(fill=X, expand=YES)
        label.pack(side=LEFT)
        entry.pack(side=LEFT, fill=X, expand=YES, padx=10)
        button.pack(side=RIGHT)

    def create_input_data_frame(self, parent: ttk.Labelframe) -> None:
        """
        Creates and formats the file path collection widgets for input data
        file.
        """
        row = ttk.Frame(parent, padding=10)
        label = ttk.Label(
            row,
            text="Input File:",
            padding=10,
        )
        entry = ttk.Entry(row, textvariable=self.input_data_file_path)
        button = ttk.Button(
            row,
            text="Pick file",
            bootstyle=SECONDARY,
            padding=10,
            width=20,
            command=lambda: self.get_filepath(self.input_data_file_path),
        )
        row.pack(fill=X, expand=YES)
        label.pack(side=LEFT)
        entry.pack(side=LEFT, fill=X, expand=YES, padx=10)
        button.pack(side=RIGHT)

    def create_env_options(self, row: ttk.Frame) -> None:
        """
        Creates the environment option radio buttons.
        """
        row_label = ttk.Label(
            row,
            text="Data environment:",
            padding=10,
        )
        row_label.pack(side=LEFT, padx=10)
        self.env_options = [("VAL", "val"), ("PROD", "prod")]
        for opt_text, opt_value in self.env_options:
            opt = ttk.Radiobutton(
                row, variable=self.selected_data_env, text=opt_text, value=opt_value
            )
            opt.pack(side=LEFT, padx=10)

    def create_type_options(self, row: ttk.Frame) -> None:
        """
        Creates the data type option combobox.
        """
        row_label = ttk.Label(
            row,
            text="Data Type:",
            padding=10,
        )
        row_label.pack(side=LEFT, padx=10)
        self.type_options = [
            "MTL GxP",
            "MTL Analytics",
            "CMD Enumeration",
            "CMD Categories",
            "CMD Tables",
            "CMD Event Frames",
            "CMD Elements",
        ]
        menu = ttk.OptionMenu(
            row, self.selected_data_type, self.type_options[0], *self.type_options
        )
        menu.pack(side=LEFT, padx=10)

    def create_version_options(self, row: ttk.Frame) -> None:
        option_label = ttk.Label(row, text="MTL Version:", padding=10)
        option_label.pack(side=LEFT, padx=10)
        entry = ttk.Entry(row, textvariable=self.selected_mtl_version)
        entry.pack(side=LEFT, padx=10)

    def create_file_options_frame(self, parent: ttk.Labelframe) -> None:
        """
        Creates the row that collects data type options.
        The data type options determine where data should be placed within
        the Design Spec Doc.
        """
        row = ttk.Frame(parent, padding=10)
        row.pack(fill=BOTH, expand=YES)
        self.create_env_options(row)
        self.create_type_options(row)
        self.create_version_options(row)

    def create_file_selection_frame(self) -> None:
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
        self.create_mtl_file_frame(frame)
        self.create_input_data_frame(frame)
        self.create_file_options_frame(frame)

    def create_preview_table_frame(self) -> None:
        """
        Creates a table to preview the new data that will append to the MTL/CMD.
        """
        _columns = [
            (0, "ID"),
            (1, "NAME"),
            (2, "DESCRIPTION"),
            (3, "SECURITY STRING"),
            (4, "DATATYPE"),
        ]
        table_frame = ttk.Frame(self.content_frame, padding=15)
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)
        table_frame.pack(fill=BOTH, expand=YES)
        self.preview_table = ttk.Treeview(table_frame, columns=_columns, show=HEADINGS)
        for key, value in _columns:
            self.preview_table.heading(key, text=value, anchor=W)
            self.preview_table.column(key, anchor=W, minwidth=50, stretch=False)
        h_scrollbar = ttk.Scrollbar(
            table_frame, orient=HORIZONTAL, command=self.preview_table.xview
        )
        v_scrollbar = ttk.Scrollbar(
            table_frame, orient=VERTICAL, command=self.preview_table.yview
        )
        self.preview_table.configure(
            xscrollcommand=h_scrollbar.set, yscrollcommand=v_scrollbar.set
        )
        self.preview_table.grid(row=0, column=0, sticky="nsew")
        h_scrollbar.grid(row=1, column=0, columnspan=2, sticky="ew")
        v_scrollbar.grid(row=0, column=1, rowspan=2, sticky="ns")

    def insert_row(self, _id, _tag, _desc, _security, _datatype) -> None:
        """
        Insert a row into the data_table.
        """
        # TODO: Actually setup data collection connections to the pandas data
        new_item = self.preview_table.insert(
            parent="", index="end", values=(_id, _tag, _desc, _security, _datatype)
        )
        self.preview_table.selection_set(new_item)
        self.preview_table.see(new_item)

    def process(self) -> None:
        """
        Run the data transfer process.
        """
        sheet_names = {
            "MTL GxP": "MTL GxP",
            "CMD Enumeration": "CMD-Enumeration Sets",
            "CMD Categories": "CMD Categories",
            "CMD Tables": "CMD Tables",
            "CMD Event Frames": "CMD-Event Frame Templates",
            "CMD Elements": "CMD-Element Tempaltes",
        }
        table_names = {
            "MTL-Analytics-VAL&PROD": "Table5",
            "MTL GxP-VAL": "Table2",
            "MTL GxP-PROD": "Table3",
            "CMD-Enumeration Sets-VAL": "Table6",
            "CMD-Enumeration Sets-PROD": "Table7",
            "CMD Categories-VAL": "Table8",
            "CMD Categories-PROD": "Table9",
            "CMD Tables-VAL": "Table10",
            "CMD Tables-PROD": "Table1012",
            "CMD-Event Frame Templates-VAL": "Table14",
            "CMD-Event Frame Templates-PROD": "Table1416",
            "CMD-Element Templates-VAL": "Table12",
            "CMD-Element Templates-PROD": "Table13",
        }
        if self.selected_data_type.get() == "MTL Analytics":
            sheet = "MTL-Analytics-VAL&PROD"
            return print(f"Selected: {sheet}, {table_names[sheet]}")
        else:
            sheet = sheet_names[self.selected_data_type.get()]
        if self.selected_data_env.get() == "prod" and sheet:
            sheet = sheet + "-PROD"
        else:
            sheet = sheet + "-VAL"
        if sheet:
            print(f"Sheet Selected: {sheet}")
            print(f"Table Selected: {table_names[sheet]}")
        else:
            print(f"ERROR SELECTING OPTIONS!")

        def subroutine():
            """
            Pushes the process of loading the information to input to another
            thread.
            """
            try:
                # load the mtl workbook
                mtl_workbook = load_workbook(self.mtl_file_path.get(), data_only=True)
                # find the appropriate table for the selected file options
                mtl_sheetname = sheet
                mtl_worksheet = mtl_workbook[mtl_sheetname]
                mtl_table_name = table_names[mtl_sheetname]
                mtl_table_range = mtl_worksheet.tables[mtl_table_name].ref
                mtl_table_data = mtl_worksheet[mtl_table_range]
                # convert the worksheet's table data string into a table
                mtl_conversion = [
                    [cell.value for cell in row] for row in mtl_table_data
                ]
                # return the header columns
                mtl_headers = mtl_conversion[0]
                mtl_rows = mtl_conversion[1:]  # Not needed for inputting data
                # convert the tabled data into a pd dataframe
                mtl_df = pd.DataFrame(mtl_rows, columns=mtl_headers)
                print("MTL Table Debug:")
                print(mtl_df)
                mtl_workbook.close()
                # testing the table by outputting the dataframe to the preview table
                input_workbook = load_workbook(
                    self.input_data_file_path.get(), data_only=True
                )
                input_worksheet = input_workbook.active
                input_conversion = list(input_worksheet.values)
                input_header = input_conversion[0]
                input_rows = input_conversion[1:]
                input_table = pd.DataFrame(input_rows, columns=input_header)
                input_workbook.close()
                print("Input data debug:")
                print(input_table)
                temp_table = input_table.copy()
                temp_table = temp_table[
                    ["Name", "Description", "datasecurity", "pointtype"]
                ]
                # adding the first few rows of data to the preview table
                for i in range(len(temp_table)):
                    self.insert_row(
                        i,
                        temp_table.iloc[i, 0],
                        temp_table.iloc[i, 1],
                        temp_table.iloc[i, 2],
                        temp_table.iloc[i, 3],
                    )
            except Exception as e:
                print(f"Could not load worksheet data.")
                print(e)
            self.window.after_idle(self.progress_bar.stop)

        self.progress_bar.start(15)
        thread = threading.Thread(target=subroutine, daemon=True)
        thread.start()

    def create_footer_frame(self) -> None:
        """
        Creates the row to manage the bottom submit/cancel buttons.
        """
        row = ttk.Frame(self.content_frame, padding=15)
        row.pack(fill=X, side=BOTTOM, anchor=S)
        self.progress_bar = ttk.Progressbar(row, mode=INDETERMINATE)
        self.progress_bar.pack(side=LEFT, expand=YES, padx=15, fill=X)
        submit_btn = ttk.Button(
            row,
            text="Process",
            bootstyle=SUCCESS,
            padding=10,
            width=20,
            command=lambda: self.process(),
        )
        submit_btn.pack(side=RIGHT, padx=15, fill=Y)
        row.configure()

    def run(self) -> None:
        """
        Runs the main process.
        """
        self.window.mainloop()


if __name__ == "__main__":
    app = App()
    app.run()
