# Copyright 2022 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
#
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH

from openpyxl import load_workbook
from tkinter.filedialog import askopenfilename as file_dialog
from ttkbootstrap.constants import (
    BOTH,
    X,
    LEFT,
    RIGHT,
    YES,
    N,
    S,
    W,
    PRIMARY,
    SECONDARY,
    SUCCESS,
    HEADINGS,
)
import pandas as pd
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

    def create_file_selection_frame(self) -> None:
        """
        Creates and formats a label frame for collecting the file paths from
        the user.
        """

        self.file_frame = ttk.Labelframe(
            self.content_frame,
            text="Select the working files",
            padding=15,
        )
        self.file_frame.pack(fill=BOTH, anchor=N)
        self.create_mtl_file_widgets()
        self.create_input_data_widgets()
        self.create_file_options_frame()

    def get_filepath(self, string_variable: ttk.StringVar) -> None:
        """
        Use file_dialog to get a file path and set it to a ttk variable.
        """
        file_types = [
            ("Supported files", ("*.xlsx", "*.xlsm", "*.csv")),
        ]
        user_input = file_dialog(title="Select a file", filetypes=file_types)
        if user_input:
            string_variable.set(user_input)
        else:
            string_variable.set("File selection canceled!")

    def create_mtl_file_widgets(self) -> None:
        """
        Creates the formats the file path collection widgets for the mtl/cmd
        file.
        """
        row = ttk.Frame(self.file_frame, padding=10)
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

    def create_input_data_widgets(self) -> None:
        """
        Creates and formats the file path collection widgets for input data
        file.
        """
        row = ttk.Frame(self.file_frame, padding=10)
        label = ttk.Label(
            row,
            text="'New Data' File:",
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

    def create_file_options_frame(self) -> None:
        """
        Creates the row that collects data type options.
        The data type options determine where data should be placed within
        the Design Spec Doc.
        """
        row = ttk.Frame(self.file_frame, padding=10)
        row.pack(fill=X, expand=YES)
        self.create_env_options(row)
        self.create_type_options(row)

    def create_preview_table_frame(self) -> None:
        """
        Creates a table to preview the new data that will append to the MTL/CMD
        """
        _columns = [
            (0, "ID"),
            (1, "NAME"),
            (2, "DESCRIPTION"),
            (3, "SECURITY STRING"),
            (4, "DATATYPE"),
        ]
        self.new_data_table = ttk.Treeview(
            self.content_frame, columns=_columns, show=HEADINGS
        )
        self.new_data_table.pack(fill=BOTH, expand=YES, pady=15)
        for i, ii in _columns:
            self.new_data_table.heading(i, text=ii, anchor=W)
            self.new_data_table.column(i, anchor=W)
        self.insert_row(0, "TEST", "THIS IS A TEST", "SRSLY JUST A TEST", "STRING")

    def insert_row(self, _id, _tag, _desc, _security, _datatype) -> None:
        """
        Insert a row into the data_table.
        """
        # TODO: Actually setup data collection connections to the pandas data
        new_item = self.new_data_table.insert(
            parent="", index="end", values=(_id, _tag, _desc, _security, _datatype)
        )
        self.new_data_table.selection_set(new_item)
        self.new_data_table.see(new_item)

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
            return print(f"Sheet Selected: {sheet}")
        else:
            sheet = sheet_names[self.selected_data_type.get()]
        if self.selected_data_env.get() == "prod" and sheet:
            sheet = sheet + "-PROD"
        else:
            sheet = sheet + "-VAL"
        if sheet:
            print(f"Sheet Selected: {sheet}")
        else:
            print(f"ERROR SELECTING OPTIONS!")
        # Gather the proper data and tables
        workbook = load_workbook(self.mtl_file_path.get(), data_only=True)
        worksheet = workbook[sheet]
        table_name = table_names[sheet]
        table_range = worksheet.tables[table_name].ref
        worksheet_data = worksheet[table_range]
        converted_data = [[cell.value for cell in row] for row in worksheet_data]
        table_header = converted_data[0]
        table_data = converted_data[1:]
        excel_table = pd.DataFrame(table_data, columns=table_header)
        workbook.close()
        print(excel_table)
        temp_table = excel_table.copy()
        temp_table = temp_table[["Name", "Description", "datasecurity", "pointtype"]]
        print(temp_table)
        for i in table_header:
            print(i)
        for i in range(16):
            self.insert_row(
                i,
                temp_table.iloc[i, 0],
                temp_table.iloc[i, 1],
                temp_table.iloc[i, 2],
                temp_table.iloc[i, 3],
            )

    def create_footer_frame(self) -> None:
        """
        Creates the row to manage the bottom submit/cancel buttons.
        """
        self.type_variable = ttk.StringVar()
        row = ttk.Frame(self.content_frame, padding=10, style="Debug.TFrame")
        row.pack(fill=X, expand=YES, anchor=S)
        submit_btn = ttk.Button(
            row,
            text="Process",
            bootstyle=SUCCESS,
            padding=10,
            width=20,
            command=lambda: self.process(),
        )
        submit_btn.pack(side=RIGHT, padx=15)

    def run(self) -> None:
        """
        Runs the main process.
        """
        self.window.mainloop()


if __name__ == "__main__":
    app = App()
    app.run()
