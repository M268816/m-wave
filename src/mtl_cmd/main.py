# Copyright 2022 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
#
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH

from tkinter.filedialog import askopenfilename as file_dialog
from ttkbootstrap.constants import *
from ttkbootstrap.widgets import scrolled as ScrolledFrame
import tkinter as tk
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

        # initialize ttk frames and widgets
        self.create_main_frame()
        self.create_file_frame()
        self.create_mtl_row()
        self.create_new_data_row()
        self.create_options_row()
        self.create_new_data_table()
        self.create_submit_button_row()

        # TODO: Use pandas to collect the new data, format, and append to the
        # TODO:     MTL database table in excel

        # TODO: Data preview table

        # TODO: Process button

        # TODO: Logging and view log button

    def create_main_frame(self) -> None:
        """
        Creates and formats the app's main workspace using a frame.
        """

        self.mainframe = ttk.Frame(self.window, padding=15)
        self.mainframe.pack(fill=BOTH)

    def create_file_frame(self) -> None:
        """
        Creates and formats a label frame for collecting the file paths from
        the user.
        """

        self.file_frame = ttk.Labelframe(
            self.mainframe, text="Select the working files", padding=15
        )
        self.file_frame.pack(fill=X, anchor=N, expand=YES)

    def create_mtl_row(self) -> None:
        """
        Creates the formats the file path collection widgets for the mtl/cmd
        file.
        """
        mtl_row = ttk.Frame(self.file_frame, padding=10)
        mtl_label = ttk.Label(
            mtl_row,
            text="MTL/CMD File:",
            padding=10,
        )
        mtl_string_var = ttk.StringVar(value="Select a file.")
        mtl_entry = ttk.Entry(mtl_row, textvariable=mtl_string_var)
        mtl_button = ttk.Button(
            mtl_row,
            text="Pick file",
            bootstyle=PRIMARY,
            padding=10,
            width=20,
            command=lambda: self.get_filepath(mtl_string_var),
        )
        mtl_row.pack(fill=X, expand=YES)
        mtl_label.pack(side=LEFT)
        mtl_entry.pack(side=LEFT, fill=X, expand=YES, padx=10)
        mtl_button.pack(side=RIGHT)

    def create_new_data_row(self) -> None:
        """
        Creates the formats the file path collection widgets for the new data
        file.
        """
        new_data_row = ttk.Frame(self.file_frame, padding=10)
        new_data_label = ttk.Label(
            new_data_row,
            text="'New Data' File:",
            padding=10,
        )
        new_string_var = ttk.StringVar(value="Select a file.")
        new_data_entry = ttk.Entry(new_data_row, textvariable=new_string_var)
        new_data_button = ttk.Button(
            new_data_row,
            text="Pick file",
            bootstyle=SECONDARY,
            padding=10,
            width=20,
            command=lambda: self.get_filepath(new_string_var),
        )
        new_data_row.pack(fill=X, expand=YES)
        new_data_label.pack(side=LEFT)
        new_data_entry.pack(side=LEFT, fill=X, expand=YES, padx=10)
        new_data_button.pack(side=RIGHT)

    def create_env_options(self, row: ttk.Frame) -> None:
        """
        Creates the environment option radio buttons.
        """
        self.env_selection = ttk.StringVar()
        row_label = ttk.Label(
            row,
            text="Data environment:",
            padding=10,
        )
        row_label.pack(side=LEFT, padx=10)
        self.env_options = [("VAL", "val"), ("PROD", "prod")]
        for opt_text, opt_value in self.env_options:
            opt = ttk.Radiobutton(
                row, variable=self.env_selection, text=opt_text, value=opt_value
            )
            opt.pack(side=LEFT, padx=10)

    def create_type_options(self, row: ttk.Frame) -> None:
        """
        Creates the data type option combobox.
        """
        self.type_selection = ttk.StringVar()
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
            row, self.type_selection, self.type_options[0], *self.type_options
        )
        menu.pack(side=LEFT, padx=10)

    def create_options_row(self) -> None:
        """
        Creates the row that collects data type options.
        The data type options determine where data should be placed within
        the Design Spec Doc.
        """
        row = ttk.Frame(self.file_frame, padding=10)
        row.pack(fill=X, expand=YES)
        self.create_env_options(row)
        self.create_type_options(row)

    def create_new_data_table(self) -> None:
        """
        Creates a table to preview the new data that will append to the MTL/CMD
        """
        _columns = [
            (0, "ID"),
            (1, "TAG/CONFIG"),
            (2, "SECURITY STRING"),
            (3, "OTHER"),
        ]
        self.new_data_table = ttk.Treeview(
            self.mainframe, columns=_columns, show=HEADINGS
        )
        self.new_data_table.pack(fill=BOTH, expand=YES, pady=15)
        for i, ii in _columns:
            self.new_data_table.heading(i, text=ii, anchor=W)
            self.new_data_table.column(i, anchor=W)
        # TODO: this is only a testing row for now
        self.insert_row()

    def create_submit_button_row(self) -> None:
        """
        Creates the row to manage the bottom submit/cancel buttons.
        """
        self.type_variable = ttk.StringVar()
        btn_frame_row = ttk.Frame(self.mainframe, padding=10)
        submit_btn = ttk.Button(
            btn_frame_row,
            text="Process",
            bootstyle=SUCCESS,
            padding=10,
            width=20,
            command=lambda: print(
                f"Pushed the button! Env Option: {self.env_selection.get()}. Type Option: {self.type_selection.get()}."
            ),
        )
        btn_frame_row.pack(fill=X, expand=YES, anchor=S)
        submit_btn.pack(side=RIGHT, padx=15)

    def process(self) -> None:
        """
        Run the data transfer process.
        """
        if self.type_selection == "MTL Analytics":
            table = "MTL-Analytics-VAL&PROD"
        elif self.env_selection == "prod":
            pass
        else:  # self.env_selectoin =="val"
            pass

    def select_data_type(self) -> None:
        """
        When a data type is selected, change the global selection variable here.
        """
        _env = self.env_selection
        _type = self.type_selection
        return print(f"Environment: {_env}. Type: {_type}.")

    def get_filepath(self, string_variable: ttk.StringVar) -> None:
        """
        Use filedialog to get the path and set to widgets and global variable.
        """
        file_types = [
            ("Supported files", ("*.xlsx", "*.xlsm", "*.csv")),
        ]
        user_input = file_dialog(title="Select a file", filetypes=file_types)
        if user_input:
            string_variable.set(user_input)
        else:
            string_variable.set("File selection canceled!")

    def insert_row(self) -> None:
        """
        Insert a row into the data_table.
        """
        # TODO: Actually setup data collection connections to the pandas data
        _ID = "ID01"
        _tag = "TAG_01"
        _sec_string = "LOTS OF INFO WILL GO HERE ENVENTUALLY"
        _other = "Filling up space"
        item_id = self.new_data_table.insert(
            parent="", index="end", values=(_ID, _tag, _sec_string, _other)
        )
        self.new_data_table.selection_set(item_id)
        self.new_data_table.see(item_id)

    def run(self) -> None:
        """
        Runs the main process.
        """
        self.window.mainloop()


if __name__ == "__main__":
    app = App()
    app.run()
