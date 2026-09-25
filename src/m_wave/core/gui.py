# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH
# This tool was created with the help of AI.

# stdlib
from tkinter import PhotoImage

# third party
import ttkbootstrap as tkb
from PIL import Image, ImageTk
from ttkbootstrap.constants import BOTH, CENTER, NSEW, PRIMARY, TOP, X
from ttkbootstrap.dialogs import Messagebox

from m_wave.core.context import AppContext
from m_wave.core.launcher import LauncherFrame
from m_wave.core.paths import PATHS
from m_wave.core.utils import (
    FONT_SMALL,
    PAD,
    PAD_X,
    PAD_Y,
    apply_scaled_geometry,
    get_user_prefs_path,
    set_config_value,
)

# local
from m_wave.core.wavepack_frame import WavePackFrame
from m_wave.wave_packs.example.gui import ExampleFrame
from m_wave.wave_packs.mtl.gui import MTLFrame

# CONSTANTS
VERSION = "1.0.0"

THEMES = (
    # Light themes
    "bootstrap-light",
    "pydata-light",
    "nord-light",
    "solarized-light",
    "catppuccin-light",
    "gruvbox-light",
    "dracula-light",
    "tokyo-night-light",
    "one-light",
    "everforest-light",
    "vapor-light",
    "minty-light",
    "pulse-light",
    "united-light",
    "sandstone-light",
    # Dark themes
    "bootstrap-dark",
    "pydata-dark",
    "nord-dark",
    "solarized-dark",
    "catppuccin-dark",
    "gruvbox-dark",
    "dracula-dark",
    "tokyo-night-dark",
    "one-dark",
    "everforest-dark",
    "vapor-dark",
    "minty-dark",
    "pulse-dark",
    "united-dark",
    "sandstone-dark",
)


class App(tkb.Window):
    """
    Root TK window. Owns the shared style object, WavePack registry, menu bar,
    and the single frame switcher container.
    """

    def __init__(self) -> None:
        super().__init__()
        self.title("λ Workbook Automation & Verification Engine | Launcher")
        apply_scaled_geometry(self, 100, 100)
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self._on_close_requested)

        self.context: AppContext = AppContext()

        # Usage, { Key: (WavePack, Description) }
        self.wavepacks: dict[str, tuple[WavePackFrame, str]] = {}

        self.active_app: WavePackFrame | None = None

        self.logo = PhotoImage(file=PATHS.logo_path)
        self.iconphoto(False, self.logo)

        self.container = tkb.Frame(self)
        self.container.pack(side=TOP, fill=BOTH, expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.build_menu()

        saved_theme = self.context.user_preferences.get("theme", "bootstrap-light")
        self.style.theme_use(saved_theme)

        self.init_wavepacks()
        self.start_launcher()

    def build_menu(self) -> None:
        """
        Construct the main application level menu bar. Call only once.
        """
        self.menubar = tkb.Menu(self)

        # File Menu
        file_menu = tkb.Menu(self.menubar, tearoff=0)  # type: ignore
        file_menu.add_command(label="Exit", command=self.destroy)
        self.menubar.add_cascade(label="File", menu=file_menu)

        # Themes
        theme_var = tkb.StringVar(
            value=self.context.user_preferences.get("theme", "litera")
        )
        self.theme_menu = tkb.Menu(self.menubar, tearoff=0)  # type: ignore
        for theme in THEMES:
            self.theme_menu.add_radiobutton(
                label=theme.capitalize(),
                value=theme,
                variable=theme_var,
                command=lambda t=theme_var: self._on_theme_change(t),
            )
        self.menubar.add_cascade(label="Themes", menu=self.theme_menu)

        # Help Menu
        self.help_menu = tkb.Menu(self.menubar, tearoff=0)  # type: ignore
        self.help_menu.add_command(label="About", command=self._show_about_window)
        self.menubar.add_cascade(label="Help", menu=self.help_menu)

        self.config(menu=self.menubar)

    def add_wavepack(self, key: str, frame_cls: WavePackFrame, desc: str) -> None:
        """
        Register a new WavePack frame class under a named key.
        """
        self.wavepacks[key] = (frame_cls, desc)

    def init_wavepacks(self) -> None:
        """
        Registers WavePacks to the applicaiton. Only registered packs can be loaded
        and initialized by the Launcher frame.
        """
        self.add_wavepack(
            "Master Tag List Processor",
            MTLFrame,  # type: ignore
            "Compare or append new PI records to the MTL/CMD.",
        )

        self.add_wavepack(
            "Example Package",
            ExampleFrame,  # type: ignore
            "This is just an example of an additional WavePack!",
        )

    def start_launcher(self) -> None:
        """
        Creates the WavePack launcher frame and attaches it to the root application.
        """
        self.launcher = LauncherFrame(self.container, self, grid_width=1)
        self.launcher.grid(row=0, column=0, sticky=NSEW)
        self.launcher.tkraise()
        self.active_app = self.launcher
        apply_scaled_geometry(self, self.launcher.width, self.launcher.height)
        self.resizable(self.launcher.resizable[0], self.launcher.resizable[1])
        self._rebuild_menu_for(self.launcher)

    def lock_wavepack(self, name: str, frame_cls: WavePackFrame) -> None:
        """
        Build the chosen WavePack, destroy the launcher screen, and update the
        window title to reflect the locked session.
        """
        app_frame = frame_cls(parent=self.container, app=self)  # type: ignore
        app_frame.grid(row=0, column=0, sticky=NSEW)
        app_frame.tkraise()
        self.active_app = app_frame
        self.launcher.destroy()

        self.title(f"λ Workbook Automation & Verification Engine | {name}")
        apply_scaled_geometry(self, app_frame.width, app_frame.height)
        self.minsize(app_frame.width_min, app_frame.height_min)
        self.resizable(app_frame.resizable[0], app_frame.resizable[1])
        self._rebuild_menu_for(self.active_app)  # type: ignore

    def _rebuild_menu_for(self, frame: WavePackFrame) -> None:
        """
        Teardown all non-fixes menus and ask the new frame to rebuild its own.
        Call on lock_wavepack() and could be called again if configs get reset.
        """
        # Remove everything exept the main menu items
        while self.menubar.index("end") > 0:  # type: ignore
            self.menubar.delete(1)

        if frame.has_new_menus:
            frame.build_menus(self.menubar)

        self.menubar.add_cascade(label="Themes", menu=self.theme_menu)
        self.menubar.add_cascade(label="Help", menu=self.help_menu)
        self._update_help_menu(frame)

    def _update_help_menu(self, frame: WavePackFrame | None = None) -> None:
        """
        Rebuild the help menu for the active frame.
        """
        self.help_menu.delete(0, "end")

        if frame is not None and frame.has_help:
            self.help_menu.add_command(
                label=f"{frame.help_label} Help", command=frame.show_help
            )
            self.help_menu.add_separator()
        self.help_menu.add_command(label="About", command=self._show_about_window)

    def _on_close_requested(self) -> None:
        """
        Warn the user if a WavePack session is active before closing.
        """
        if self.active_app is not None:
            confirmed = Messagebox.yesno(
                title="Confirm Exit.",
                message=(
                    "A session is active.\n\n"
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
        set_config_value(
            get_user_prefs_path(), self.context.user_preferences, config_key, var
        )

    def _on_theme_change(self, theme: tkb.StringVar) -> None:
        """
        If the theme changes, try to set the config value, if true (success),
        change the theme.
        """
        if set_config_value(
            get_user_prefs_path(), self.context.user_preferences, "theme", theme
        ):
            self.style.theme_use(theme.get())

    def _show_about_window(self) -> None:
        """
        Creates and displays a toplevel modal window with 'about' information.
        """
        about = tkb.Toplevel()
        about.title("About")
        about.iconphoto(False, self.logo)
        about.lift()
        about.focus_force()
        about.grab_set()

        container = tkb.Frame(about, padding=PAD)
        container.pack(expand=True, fill=BOTH)

        img = Image.open(PATHS.logo_path)
        img = img.resize((128, 128), Image.LANCZOS)  # type: ignore
        self._about_img = ImageTk.PhotoImage(img)

        canv = tkb.Label(
            container,
            image=self._about_img,
            anchor=CENTER,
        )
        canv.pack(fill=X)

        ver = tkb.Label(
            container,
            font=FONT_SMALL,
            text=f"Workbook Automation & Verification Engine\nVersion: {VERSION}",
            padding=PAD,
        )
        ver.pack(fill=X)

        tkb.Separator(container, orient="horizontal", bootstyle=PRIMARY).pack(fill=X)

        cright = (
            "Copyright 2026\n\n"
            + "Merck KGaA, Darmstadt Germany and/or its affiliates.\n"
            + "All right reserved"
        )
        cright_label = tkb.Label(
            container,
            font=FONT_SMALL,
            text=cright,
            padding=PAD,
        )
        cright_label.pack(fill=X)

        tkb.Separator(container, orient="horizontal", bootstyle=PRIMARY).pack(fill=X)

        auth = (
            "Authored by:\nRaymond Comeau\n"
            + "MilliporeSigma Data Systems Technician\n"
            + "Jaffrey, NH"
        )
        auth_label = tkb.Label(
            container,
            font=FONT_SMALL,
            text=auth,
            padding=PAD,
        )
        auth_label.pack(fill=X)

        close_btn = tkb.Button(container, text="Nice", command=about.destroy)
        close_btn.pack(padx=PAD_X, pady=PAD_Y)

        def _on_resize(event):
            cright_label.config(wraplength=event.width)
            auth_label.config(wraplength=event.width)
            ver.config(wraplength=event.width)

        container.bind("<Configure>", _on_resize)

        about.resizable(False, False)

    def run(self) -> None:
        self.mainloop()
