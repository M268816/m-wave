from tkinter import filedialog
import tkinter as tk
import ttkbootstrap as ttk


class Config:
    """
    Returns a tuple of filepaths. (MTL/CVS Location, New Data Location)
    """

    def __init__(self, parent) -> None:
        # tk modal/root
        self.modal = ttk.Toplevel(parent)
        self.modal.title("Choose file paths.")
        self.modal.geometry("360x240")
        self.modal.minsize(200, 200)
        self.modal.maxsize(500, 500)

        # mtl input
        self.mtl_label = ttk.Label(self.modal, text="MTL/CMD Location.")
        self.mtl_input_string = tk.StringVar(value="This is the default input.")
        self.mtl_input = ttk.Entry(
            self.modal,
            textvariable=self.mtl_input_string,
            width=len(self.mtl_input_string.get()),
        )
        self.mtl_pick_file_button = ttk.Button(
            self.modal,
            text="Select file",
            command=lambda: self.pick_file(self.mtl_input_string, self.mtl_input),
        )

        # new entries input
        self.entries_label = ttk.Label(self.modal, text="New entries locaiton.")
        self.entries_input_string = tk.StringVar(value="This is the default input.")
        self.entries_input = ttk.Entry(
            self.modal,
            textvariable=self.entries_input_string,
            width=len(self.entries_input_string.get()),
        )
        self.entries_pick_file_button = ttk.Button(
            self.modal,
            text="Select file",
            command=lambda: self.pick_file(
                self.entries_input_string, self.entries_input
            ),
        )

        # submit button
        self.submit_btn = ttk.Button(self.modal, text="Submit", command=self.submit)

        self.format_layout()

    def format_layout(self) -> None:
        """
        Format the dialog's layout.
        """
        self.mtl_label.pack()
        self.mtl_input.pack()
        self.mtl_pick_file_button.pack()

        self.entries_label.pack(pady=(5, 0))
        self.entries_input.pack()
        self.entries_pick_file_button.pack()

        self.submit_btn.pack(pady=15)

    def pick_file(
        self,
        input_string: tk.StringVar,
        entry_widget: ttk.Entry,
        file_type: tuple = ("All Supported", ("*.xlsx", "*.xlsm", "*.csv")),
    ) -> None:
        """
        Use filedialog to pick a file name.
        """
        _filetypes = [
            file_type,
        ]

        _path = filedialog.askopenfilename(title="Select a file.", filetypes=_filetypes)

        if _path:
            input_string.set(_path)
            entry_widget.config(width=min(len(_path), 100))
        else:
            input_string.set("File not picked!")
            entry_widget.config(width=min(len(input_string.get()), 100))

    def submit(self) -> None:
        """
        Clicking the submit button runs this method.
        """
        self.modal.destroy()

    def run(self) -> tuple:
        self.modal.wait_window()

        _mtl_path = self.mtl_input_string.get()
        _entry_path = self.entries_input_string.get()

        return (_mtl_path, _entry_path)


if __name__ == "__main__":
    module = Config(None)
    for _string in module.run():
        print(_string)
