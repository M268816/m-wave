import json
import logging
import os
from tkinter import filedialog
import tkinter as tk
import tkinter.ttk as ttk

class Configure:
    def __init__(self) -> None:
        print("Hello, from the configuration!")
        self.window = tk.Tk()
        self.window.title("MTL/CMD data append tool.")

        self.label = ttk.Label(self.window, text="This is a label.")
        self.label.pack()

        self.input_string = tk.StringVar(value="This is the default input.")
        self.input = ttk.Entry(self.window, textvariable=self.input_string)
        self.input.pack()

        self.pick_file_button = ttk.Button(
                self.window,
                text="Select file",
                command=self.pick_file
                )
        self.pick_file_button.pack()

    def pick_file(self) -> str:
        '''
        Use filedialog to pick a file name.
        '''
        _path = filedialog.askdirectory(title="Select a file.")
        if _path:
            return _path
        else:
            return ""

    def run(self) -> None:
        self.window.mainloop()

if __name__ == "__main__":
    module = Configure()
    module.run()
