# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
##
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH

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
    FONT_SMALL,
    PAD,
    PAD_X,
    PAD_Y,
    H1,
    FONT,
    WavePackFrame,
)
from src.kepware.gui import KepwareFrame
from src.mtl.gui import MTLFrame
from src.example.gui import ExampleFrame
from src.tag_doc_gen.gui import TagDocGenFrame

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
    Root TK window. Owns the shared style object, WavePack registry, menu bar,
    and the single frame switcher container.
    """

    def __init__(self) -> None:
        super().__init__()

        self.controller: AppController = AppController(self)

        # Usage, { Key: (WavePack, Description) }
        self.wavepacks: dict[str, tuple[WavePackFrame, str]] = {}

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

        self.init_wavepacks()
        self.start_launcher()

    def init_wavepacks(self) -> None:
        self.add_wavepack(
            "Master Tag List Processor",
            MTLFrame,  # type: ignore
            "Compare or append new PI AF records to the MTL/CMD.",
        )
        self.add_wavepack(
            "Example Package",
            ExampleFrame,  # type: ignore
            "This is just an example of an additional WavePack!",
        )
        self.add_wavepack(
            "Kepware Environment Comparison",
            KepwareFrame,  # type: ignore
            "Compare environment (VAL, DEV) CSV tag exports.",
        )
        self.add_wavepack(
            "Tag Document Genereator",
            TagDocGenFrame,  # type: ignore
            "Generate Kepware/PI tag documents.",
        )

    def add_wavepack(self, key: str, frame_cls: WavePackFrame, desc: str) -> None:
        """
        Register a new WavePack frame class under *name*.
        """
        self.wavepacks[key] = (frame_cls, desc)

    def start_launcher(self) -> None:
        self.launcher = LauncherFrame(self.container, self, grid_width=1)
        self.launcher.grid(row=0, column=0, sticky=NSEW)
        self.launcher.tkraise()
        self.geometry(f"{self.launcher.width}x{self.launcher.height}")
        self.resizable(self.launcher.resizable[0], self.launcher.resizable[1])

    def lock_wavepack(self, name: str, frame_cls: WavePackFrame) -> None:
        """
        Build the chosen WavePack, destroy the launcher screen, and update the
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
        help_menu.add_command(label="About", command=self._show_about_window)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.config(menu=menubar)

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
        webbrowser.open(vid_link, new=1)
        webbrowser.open(git_url, new=2)

    def _show_about_window(self) -> None:
        about = tkb.Toplevel()
        about.title("About")
        about.iconphoto(False, self.logo)
        about.lift()
        about.focus_force()
        about.grab_set()

        container = tkb.Frame(about, padding=PAD)
        container.pack(expand=True, fill=BOTH)

        img = Image.open(str(LOGO_PATH))
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
            text="Workbook Automation & Verification Engine\nVersion: 0.1.0.prealpha.5",
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


class LauncherFrame(WavePackFrame):
    """
    WavePack selection screen shown at startup.

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
            height=360,
            height_min=360,
            width=480,
            width_min=480,
            resizable=(False, False),
        )
        self.window = window
        self.grid_width = grid_width

        tkb.Label(self, text="Select a Session Type", font=H1).pack(
            padx=PAD_X, pady=PAD_Y
        )
        tkb.Label(
            self,
            text=(
                "You will be locked into your session type\n"
                "(also called a Wave Process Package or WavePack)\n"
                "for the duration of your session.\n"
                "Restart the application to change sessions.\n"
                "Currently, only the MTL WavePack is available.\n"
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

        for index, (name, info) in enumerate(self.window.wavepacks.items()):
            frame_cls = info[0]
            desc = info[1]
            row = index // self.grid_width
            col = index % self.grid_width

            f = tkb.Frame(self.scroll_frame)
            f.grid(row=row, column=col, padx=PAD_X, pady=PAD_Y, sticky=NSEW)

            tkb.Button(
                f,
                text=name,
                width=32,
                command=lambda n=name, fc=frame_cls: self._confirm_and_launch(n, fc),
            ).grid(row=0, column=0, padx=PAD_X, pady=PAD_Y)

            tkb.Label(
                f,
                text=desc,
                justify="left",
                wraplength=180,
            ).grid(row=0, column=1, padx=PAD_X, pady=PAD_Y, sticky=NSEW)

        for col in range(self.grid_width):
            self.scroll_frame.columnconfigure(col, weight=1)

    def _confirm_and_launch(self, name: str, frame_cls: WavePackFrame) -> None:
        """
        Ask the user to confirm the WavePack before locking in.
        """
        confirmed = Messagebox.yesno(
            title="Confirm Session",
            message=(
                f"You are about to start a session with WavePack:\n    {name}\n"
                "You cannot change sessions without restarting.\n\n"
                "Continue?"
            ),
        )
        if confirmed == "Yes":
            self.window.lock_wavepack(name, frame_cls)
