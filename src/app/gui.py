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
"""

# stdlib
import webbrowser

# third party
from PIL import Image, ImageTk
import ttkbootstrap as tkb
from ttkbootstrap.constants import (
    BOTH,
    CENTER,
    NSEW,
    TOP,
    X,
)
from ttkbootstrap.dialogs import Messagebox
from ttkbootstrap.widgets.scrolled import ScrolledFrame
from ttkbootstrap.style import PRIMARY

# local
from src.app.paths import LOGO_PATH, INSTRUCTIONS_PATH, USER_PREFS_PATH
from src.app.controller import (
    AppController,
)
from src.app.utils import (
    ProtocolFrame,
    PAD,
    PAD_X,
    PAD_Y,
    H1,
    FONT,
)
from src.mtl.gui import MTLFrame
from src.tag_formatter.gui import TagFormatterFrame

# CONSTANTS
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
    MTL_INSTRUCTIONS = f.read()


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
        self.geometry("100x100")
        self.resizable(False, False)
        self.logo = tkb.PhotoImage(file=str(LOGO_PATH))
        self.iconphoto(False, self.logo)
        self.protocol("WM_DELETE_WINDOW", self._on_close_requested)

        self.container = tkb.Frame(self)
        self.container.pack(side=TOP, fill=BOTH, expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self._build_menu()

        saved_theme = self.controller.user_preferences.get("theme", "litera")
        self.style.theme_use(saved_theme)

        self.init_protocols()
        self.start_launcher()

    def init_protocols(self) -> None:
        self.add_protocol("MTL-CMD", MTLFrame)  # type: ignore
        # self.add_protocol("Tag Formatter", TagFormatterFrame)  # type: ignore
        self.add_protocol("Example", ExampleFrame)  # type: ignore

    def start_launcher(self) -> None:
        self.launcher = LauncherFrame(self.container, self, grid_width=1)
        self.launcher.grid(row=0, column=0, sticky=NSEW)
        self.launcher.tkraise()
        self.geometry(f"{self.launcher.height}x{self.launcher.width}")
        self.resizable(self.launcher.resizable[0], self.launcher.resizable[1])

    def add_protocol(self, name: str, frame_cls: ProtocolFrame) -> None:
        """
        Register a new protocol frame class under *name*.
        """
        self.protocols[name] = frame_cls

    def lock_protocol(self, name: str, frame_cls: ProtocolFrame) -> None:
        """
        Build the chosen protocol, destroy the launcher screen, and update the
        window title to reflect the locked session.
        """
        app_frame = frame_cls(parent=self.container, window=self)  # type: ignore
        app_frame.grid(row=0, column=0, sticky=NSEW)
        app_frame.tkraise()
        self.controller.set_process_controller(app_frame.proc_ctrl)
        self.active_app = app_frame
        self.launcher.destroy()

        self.title(f"λ Workbook Automation & Verification Engine | {name}")
        self.geometry(f"{app_frame.width}x{app_frame.height}")
        self.minsize(app_frame.width_min, app_frame.height_min)
        self.resizable(app_frame.resizable[0], app_frame.resizable[1])

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
            cfg_var = tkb.BooleanVar(
                value=self.controller.user_preferences.get(key, False)
            )
            report_menu.add_checkbutton(
                label=menu_label,
                variable=cfg_var,
                command=lambda k=key, v=cfg_var: self._on_option_change(k, v),
            )
        menubar.add_cascade(label="Report Options", menu=report_menu)

        # Themes
        theme_var = tkb.StringVar(
            value=self.controller.user_preferences.get("theme", "litera")
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
        help_menu.add_command(
            label="MTL/CMD Instructions", command=self._show_mtl_instructions
        )
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
            if confirmed == "No":
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
        """
        If an option changes, try to set the config value.
        """
        self.controller.set_config_value(
            USER_PREFS_PATH, self.controller.user_preferences, config_key, var
        )

    def _on_theme_change(self, theme: tkb.StringVar) -> None:
        """
        If the theme changes, try to set the config value, if true (success), change the theme.
        """
        if self.controller.set_config_value(
            USER_PREFS_PATH, self.controller.user_preferences, "theme", theme
        ):
            self.style.theme_use(theme.get())

    def _show_mtl_instructions(self) -> None:
        self.controller.report.info(
            "Instructions sent.",
            log=False,
            verbose=False,
        )
        self.controller.report.info(MTL_INSTRUCTIONS, log=False, verbose=False)
        git_url = self.controller.mtl_configs["mtl_instructions_git_url"]
        vid_link = self.controller.mtl_configs["mtl_help_vid_url"]
        webbrowser.open(git_url)
        webbrowser.open_new_tab(vid_link)


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

    def __init__(
        self, parent: tkb.Frame, window: AppWindow, grid_width: int = 3
    ) -> None:
        super().__init__(
            parent,
            height=640,
            height_min=640,
            width=480,
            width_min=480,
            resizable=(False, False),
        )
        self.window = window
        self.grid_width = grid_width

        tkb.Label(self, text="Select Protocol", font=H1).pack(padx=PAD_X, pady=PAD_Y)
        tkb.Label(
            self,
            text=(
                "You will be locked into your protocol\n"
                "selection for the duration of your session.\n"
                "Restart the application to change protocols.\n"
                "\n"
                "Currently, only the MTL-CMD protocol is available.\n"
            ),
            font=FONT,
            foreground="gray",
            justify=CENTER,
        ).pack(pady=PAD_Y)

        tkb.Separator(self, orient="horizontal", bootstyle=PRIMARY).pack(
            fill=X, padx=PAD_X
        )

        self.scroll_frame = ScrolledFrame(self, padding=PAD)
        self.scroll_frame.pack(fill=BOTH, padx=PAD_X, pady=PAD_Y, expand=True)

        for index, (name, frame_cls) in enumerate(self.window.protocols.items()):
            row = index // self.grid_width
            col = index % self.grid_width
            tkb.Button(
                self.scroll_frame,
                text=name,
                width=24,
                command=lambda n=name, fc=frame_cls: self._confirm_and_launch(n, fc),
            ).grid(row=row, column=col, padx=PAD_X, pady=PAD_Y, sticky=NSEW)

        for col in range(self.grid_width):
            self.scroll_frame.columnconfigure(col, weight=1)

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
        if confirmed == "Yes":
            self.window.lock_protocol(name, frame_cls)

    def on_teardown(self) -> None:
        """
        Called by AppWindow before the application closes.
        """
        pass


class ExampleFrame(ProtocolFrame):
    def __init__(
        self,
        parent: tkb.Frame,
        window: AppWindow,
    ) -> None:
        super().__init__(
            parent,
            height=320,
            height_min=320,
            width=320,
            width_min=320,
            resizable=(True, True),
        )
        self.window = window
        # A process controller must be created to handle the process thread
        # self.proc_ctrl: ExampleProcess = ExampleProcess(window)

        self.container = tkb.Frame(self, padding=PAD)
        self.container.pack(side=TOP, fill=BOTH, expand=True)

        self.label_var = tkb.StringVar(value="Hello, World.")
        self.label = tkb.Label(
            self.container,
            textvariable=self.label_var,
            background="yellow",
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
