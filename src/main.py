from tkinter.filedialog import askopenfilename as file_dialog
import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *


class App:
    """
    MTL/CMD new data formatter.
    """

    def __init__(self) -> None:
        # create main tkiner window with bootstrap
        self.window = ttk.Window(
            title="Master Tag List new data formatter.",
            themename="superhero",
            size=(640, 360),
            minsize=(640, 360),
        )

        # creates the file selection frame and widgets
        self.create_main_frame()
        self.create_file_frame()
        self.create_mtl_frame_row()
        self.create_new_data_frame_row()
        self.create_data_type_row()
        self.create_new_data_table()
        self.create_submit_button_row()

        # TODO: Use pandas to collect the new data, format, and append to the
        # TODO:     MTL database table in excel

        # TODO: Data preview table

        # TODO: Process button

        # TODO: Logging and view log button

    def create_main_frame(self) -> None:
        """
        Creates and formats the app's main work space using a frame.
        """

        self.mainframe = ttk.Frame(self.window, padding=15)
        self.mainframe.pack(fill=BOTH)

    def create_file_frame(self) -> None:
        """
        Creates and formats the label frame for collecting the file paths from
        the user.
        """

        self.file_frame = ttk.Labelframe(
            self.mainframe, text="Select the working files", padding=15
        )
        self.file_frame.pack(fill=X, anchor=N, expand=YES)

    def create_mtl_frame_row(self) -> None:
        """
        Creates the formats the file collection widgets for the file frame.
        """
        mtl_frame_row = ttk.Frame(self.file_frame, padding=10)
        mtl_frame_label = ttk.Label(
            mtl_frame_row,
            text="MTL/CMD File:",
            padding=10,
        )
        mtl_text_variable = ttk.StringVar(value="Select a file.")
        mtl_frame_entry = ttk.Entry(mtl_frame_row, textvariable=mtl_text_variable)
        mtl_frame_button = ttk.Button(
            mtl_frame_row,
            text="Pick file",
            bootstyle=PRIMARY,
            padding=10,
            width=20,
            command=lambda: self.get_filepath(mtl_frame_entry, mtl_text_variable),
        )
        mtl_frame_row.pack(fill=X, expand=YES)
        mtl_frame_label.pack(side=LEFT)
        mtl_frame_entry.pack(side=LEFT, fill=X, expand=YES, padx=10)
        mtl_frame_button.pack(side=RIGHT)

    def create_new_data_frame_row(self) -> None:
        """
        Creates the formats the file collection widgets for the file frame.
        """
        new_frame_row = ttk.Frame(self.file_frame, padding=10)
        new_frame_label = ttk.Label(
            new_frame_row,
            text="'New Data' File:",
            padding=10,
        )
        new_text_variable = ttk.StringVar(value="Select a file.")
        new_frame_entry = ttk.Entry(new_frame_row, textvariable=new_text_variable)
        new_frame_button = ttk.Button(
            new_frame_row,
            text="Pick file",
            bootstyle=SECONDARY,
            padding=10,
            width=20,
            command=lambda: self.get_filepath(new_frame_entry, new_text_variable),
        )
        new_frame_row.pack(fill=X, expand=YES)
        new_frame_label.pack(side=LEFT)
        new_frame_entry.pack(side=LEFT, fill=X, expand=YES, padx=10)
        new_frame_button.pack(side=RIGHT)

    def create_data_type_row(self) -> None:
        """
        Creates the row to manage the data type selection.
        """
        self.type_variable = ttk.StringVar()
        type_frame_row = ttk.Frame(self.file_frame, padding=10)
        type_frame_label = ttk.Label(
            type_frame_row,
            text="Data Type:",
            padding=10,
        )
        mtl_option = ttk.Radiobutton(
            type_frame_row, text="MTL", variable=self.type_variable, value="mtl"
        )
        cmd_option = ttk.Radiobutton(
            type_frame_row, text="CMD", variable=self.type_variable, value="CMD"
        )
        type_frame_row.pack(fill=X, expand=YES)
        type_frame_label.pack(side=LEFT, padx=10)
        mtl_option.pack(side=LEFT, padx=10)
        cmd_option.pack(side=LEFT, padx=10)
        # INFO: Starts with MTL type selected by default
        # INFO: Change this later maybe?
        mtl_option.invoke()

    def create_new_data_table(self) -> None:
        """
        Creates a table to preview the new data that will append to the MTL/CMD
        """
        self.new_data_table = ttk.Treeview(
            self.mainframe, columns=[0, 1, 2, 3], show=HEADINGS
        )
        self.new_data_table.heading(0, text="ID", anchor=W)
        self.new_data_table.heading(1, text="TAG/CONFIG", anchor=W)
        self.new_data_table.heading(2, text="SECURITY STRING", anchor=W)
        self.new_data_table.heading(3, text="OTHER", anchor=W)
        self.new_data_table.column(0, anchor=W)
        self.new_data_table.column(1, anchor=W)
        self.new_data_table.column(2, anchor=W)
        self.new_data_table.column(3, anchor=W)

        self.new_data_table.pack(fill=BOTH, expand=YES, pady=15)
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
            command=lambda: print("Pushed the button!"),
        )
        btn_frame_row.pack(fill=X, expand=YES, anchor=S)
        submit_btn.pack(side=RIGHT, padx=15)

    def get_filepath(
        self, entry_widget: ttk.Entry, string_variable: ttk.StringVar
    ) -> None:
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
