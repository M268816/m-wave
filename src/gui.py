# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
#
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH

"""
The GUI classes within this module are used to control the display of the application.

Classes
-------
AppWindow
    The root TK window.
LauncherFrame
    GUI controller for protocol selection, the "protocol launcher".
MESFrame
    GUI controller of the MESGui protocol.
MTLFrame
    GUI controller of the MTLGUI protocol.
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
    CENTER,
    INDETERMINATE,
    LEFT,
    N,
    NO,
    NSEW,
    RIGHT,
    S,
    TOP,
    X,
    Y,
    YES,
)
from ttkbootstrap.style import PRIMARY, SUCCESS
from ttkbootstrap.dialogs import Messagebox

# local
from src.metadata import MTL_VERSION, WORKSHEET_METADATA
from src.paths import LOGO_PATH, INSTRUCTIONS_PATH
from src.logic import (
    AppController,
    MTLController,
    MESController,
    ProcessController,
    ProcessRequest,
    ProcessType,
    ProcessUi,
)

# CONSTANTS
LAUNCH_SIZE = (360, 360)
APP_SIZE = (850, 525)
APP_MINSIZE = (850, 525)

H1 = ("Verdana", 20, font.BOLD)
H2 = ("Verdana", 16, font.NORMAL)
H3 = ("Verdana", 14, font.NORMAL)
H4 = ("Verdana", 12, font.NORMAL)
FONT = ("Verdana", 10, font.NORMAL)

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


class ProtocolFrame(tkb.Frame):
    """
    Class helper for type assignment
    """

    def __init__(self, parent: tkb.Frame) -> None:
        super().__init__(parent)
        self.proc_ctrl: ProcessController


class AppWindow(tkb.Window):
    """
    Root TK window. Owns the shared style object, protocol registry, menubar,
    and the single frame switcher container.

    Parameters
    ----------
    controller : AppController
        Business logic controller injected at construction time.
    """

    def __init__(self) -> None:
        super().__init__()

        self.controller: AppController = AppController(self)
        self.protocols: dict[str, ProtocolFrame] = {}
        self.active_app = None

        self.title("λ Workbook Automation & Verification Engine | Launcher")
        self.geometry(f"{LAUNCH_SIZE[0]}x{LAUNCH_SIZE[1]}")
        self.resizable(False, False)
        self.logo = tkb.PhotoImage(file=str(LOGO_PATH))
        self.iconphoto(False, self.logo)
        self.protocol("WM_DELETE_WINDOW", self._on_close_requested)

        self.container = tkb.Frame(self)
        self.container.pack(side=TOP, fill=BOTH, expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self._build_menu()

        saved_theme = self.controller.user_configs.get("theme", "litera")
        self.style.theme_use(saved_theme)

        self.add_protocol("MTL-CMD", MTLFrame)
        self.add_protocol("Example", ExampleFrame)
        # self.add_protocol("MES", MESFrame)

        self.launcher = LauncherFrame(self.container, self)
        self.launcher.grid(row=0, column=0, sticky=NSEW)
        self.launcher.tkraise()

    def add_protocol(self, name: str, frame_cls: ProtocolFrame) -> None:
        """
        Register a new protocol frame class under *name*.
        """
        self.protocols[name] = frame_cls

    def lock_protocol(self, frame_cls: ProtocolFrame) -> None:
        """
        Build the chosen protocol, destroy the launcher screen, and update the
        window title to reflect the locked session.
        """
        app_frame = frame_cls(parent=self.container, window=self)
        app_frame.grid(row=0, column=0, sticky=NSEW)
        app_frame.tkraise()
        self.controller.set_process_controller(app_frame.proc_ctrl)
        self.active_app = app_frame
        self.launcher.destroy()

        self.title(
            f"λ Workbook Automation & Verification Engine | {app_frame.__class__.__name__}"
        )
        self.geometry(f"{APP_SIZE[0]}x{APP_SIZE[1]}")
        self.minsize(APP_MINSIZE[0], APP_MINSIZE[1])
        self.resizable(True, True)

    def run(self) -> None:
        self.mainloop()

    def _build_menu(self) -> None:
        """
        Construct the application level menu bar.
        """
        menubar = tkb.Menu(self)

        # File Menu
        file_menu = tkb.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Exit", command=self.destroy)
        menubar.add_cascade(label="File", menu=file_menu)

        # Report Options
        report_menu = tkb.Menu(menubar, tearoff=0)
        for menu_label, key in (
            ("Report Timestamps", "use_timestamps"),
            ("Report Message Types", "use_msg_types"),
        ):
            cfg_var = tkb.BooleanVar(value=self.controller.user_configs.get(key, False))
            report_menu.add_checkbutton(
                label=menu_label,
                variable=cfg_var,
                command=lambda k=key, v=cfg_var: self._on_option_change(k, v),
            )
        menubar.add_cascade(label="Report Options", menu=report_menu)

        # Themes
        theme_var = tkb.StringVar(
            value=self.controller.user_configs.get("theme", "litera")
        )
        theme_menu = tkb.Menu(menubar, tearoff=0)
        for theme in THEMES:
            theme_menu.add_radiobutton(
                label=theme.capitalize(),
                value=theme,
                variable=theme_var,
                command=lambda t=theme_var: self._on_theme_change(t),
            )
        menubar.add_cascade(label="Themes", menu=theme_menu)

        # Help Menu
        help_menu = tkb.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Instructions", command=self._show_instructions)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.config(menu=menubar)

    def _on_close_requested(self) -> None:
        """
        Warn the user if a protocol session is active before closing.
        """
        if self.active_app is not None:
            confirmed = Messagebox.yesno(
                title="Confirm Exit.",
                message=(
                    "A protocol session is active.\n\n"
                    "Are you sure you want to exit?\n"
                    "Any unsaved work will be lost."
                ),
            )
            if not confirmed:
                return
            try:
                self.active_app.on_teardown()  # type: ignore
            except Exception as e:
                Messagebox.show_warning(
                    title="Cleanup Warning",
                    message=f"Teardown encountered an issue:\n{e}",
                )
        self.destroy()

    def _on_option_change(self, config_key: str, var: tkb.BooleanVar) -> None:
        self.controller.set_config_value(config_key, var)

    def _on_theme_change(self, theme: tkb.StringVar) -> None:
        self.style.theme_use(theme.get())
        self.controller.set_config_value("theme", theme)

    def _show_instructions(self) -> None:
        self.controller.report.info(
            "Instructions pushed to the text display",
            log=False,
            verbose=False,
            popup=True,
        )
        self.controller.report.info(INSTRUCTIONS, log=False, verbose=False)


class LauncherFrame(ProtocolFrame):
    """
    Protocol selection screen shown at startup.

    Parameters
    ----------
    parent: tkb.Frame
        The main container owned by AppWindow
    window: AppWindow
        A back reference to the root window.
    """

    def __init__(self, parent: tkb.Frame, window: AppWindow) -> None:
        super().__init__(parent)
        self.window = window

        tkb.Label(self, text="Select Protocol", font=H1).pack(padx=PAD_X, pady=PAD_Y)
        tkb.Label(
            self,
            text=(
                "You will be locked into your protocol\n"
                "selection for the duration of your session.\n"
                "Restart the application to change protocols."
            ),
            font=FONT,
            foreground="gray",
            justify=CENTER,
        ).pack(pady=PAD_Y)

        for name, frame_cls in self.window.protocols.items():
            tkb.Button(
                self,
                text=name,
                width=25,
                command=lambda n=name, fc=frame_cls: self._confirm_and_launch(n, fc),
            ).pack(pady=PAD_Y)

    def _confirm_and_launch(self, name: str, frame_cls: ProtocolFrame) -> None:
        """
        Ask the user to confirm the protocol before locking in.
        """
        confirmed = Messagebox.yesno(
            title="Confirm Protocol",
            message=(
                f"You are about to start a session with procol:\n    {name}\n"
                "You cannot change protocols without restarting.\n\n"
                "Continue?"
            ),
        )
        if confirmed:
            self.window.lock_protocol(frame_cls)

    def on_teardown(self) -> None:
        """
        Called by AppWindow before the application closes.
        """
        pass


class ExampleFrame(ProtocolFrame):
    def __init__(self, parent: tkb.Frame, window: AppWindow) -> None:
        super().__init__(parent)
        self.window = window
        # A process controller must be created to handle the process thread
        # self.proc_ctrl: ExampleProcess = ExampleProcess(window)

        self.container = tkb.Frame(self, padding=PAD)
        self.container.pack(side=TOP, fill=BOTH, expand=True)

        self.label_var = tkb.StringVar(value="Hello, World.")
        self.label = tkb.Label(
            self.container,
            textvariable=self.label_var,
            background="gray",
            justify=CENTER,
            anchor=CENTER,
        )
        self.label.pack(
            expand=True,
            fill=X,
            side=TOP,
        )

        self.button_var = tkb.StringVar(value="Click me.")
        self.button = tkb.Button(
            self.container,
            textvariable=self.button_var,
            padding=PAD,
            width=32,
            command=self._on_button_pressed,
        )
        self.button.pack(side=TOP)

    def _on_button_pressed(self) -> None:
        Messagebox.ok(title="Hello", message="You pressed the button!")


class MESFrame(ProtocolFrame):
    """
    Placeholder MES not actually created yet.

    Master controller of the MES protocol GUI and its object variables.

    Attributes
    ----------
    parent: tkb.Frame
        The main container owned by AppWindow
    window: tkb.WinESw
        A back reference to the root window

    Methods
    -------
    run()
        Starts the tk window main loop

    """

    def __init__(self, parent: tkb.Frame, window: AppWindow) -> None:
        super().__init__(parent)
        self.window = window
        self.proc_ctrl: MESController = MESController(window)

        self.container = tkb.Frame(self, padding=PAD)
        self.container.pack(side=TOP, fill=X, expand=True)

        self.label = tkb.Label(
            self.container,
            text="MES APP",
            justify=CENTER,
            padding=PAD,
            font=FONT,
            background="tan",
        ).pack(
            side=TOP,
            expand=YES,
            fill=BOTH,
            padx=PAD_X,
            pady=PAD_Y,
        )

    def on_teardown(self) -> None:
        """
        Called by AppWindow before the application closes
        """
        pass


class MTLFrame(ProtocolFrame):
    """
    Master controller of the MTL/CMD protocol GUI and its object variables.

    Parameters
    ----------
    parent: tkb.Frame
        The main container owned by AppWindow
    window: tkb.Window
        A back reference to the root window
    """

    def __init__(self, parent: tkb.Frame, window: AppWindow) -> None:
        super().__init__(parent)
        self.window = window
        self.proc_ctrl: MTLController = MTLController(window)
        self.stext = ScrolledText()

        # TK Variables options
        self.opt_data_table = tkb.StringVar()
        self.opt_mtl_path = tkb.StringVar(value="Select a file.")
        self.opt_input_path = tkb.StringVar(value="Select a file.")
        self.opt_filter = tkb.StringVar()
        self.opt_process = tkb.IntVar(value=ProcessType.NONE.value)
        self.mtl_version = tkb.StringVar(value=MTL_VERSION)
        self._mtl_is_selected = tkb.BooleanVar(value=False)
        self._input_is_selected = tkb.BooleanVar(value=False)

        # Main content frame
        self.container = ttk.Frame(self, padding=PAD)
        self.container.pack(side=TOP, fill=BOTH, expand=YES)

        self._build_file_select()
        self._build_config_options()
        self._build_process_row()
        self._build_text_display()

        self.report.info(
            "Welcome to the WAVE. Start the process by choosing your files.", log=False
        )
        self.report.info("For more information please use the Help Menu.", log=False)

    @property
    def report(self):
        return self.window.controller.report

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

        self._build_file_row(
            frame,
            "Select MTL/CMD:",
            self.opt_mtl_path,
            self._mtl_is_selected,
            20,
        )
        self._build_file_row(
            frame,
            "Select input CSV:",
            self.opt_input_path,
            self._input_is_selected,
            20,
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
        frame = tkb.Labelframe(self.container, text="Process Output.")
        frame.pack(side=TOP, fill=BOTH, expand=YES)
        # frame.pack_propagate(False)
        mono = font.nametofont("TkFixedFont")
        self.stext = ScrolledText(frame, height=24)
        self.stext.configure(font=mono)
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
            self.report.error("Please select both files to start process.")
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

        self.proc_ctrl.start_process(req, ui)

    def on_teardown(self) -> None:
        """
        Called by AppWindow before the application closes.
        """
        pass
