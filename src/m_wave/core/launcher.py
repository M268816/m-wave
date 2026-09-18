# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH
# This tool was created with the help of AI.

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from m_wave.core.gui import App

# stdlib
from tkinter import font

# third party
import ttkbootstrap as tkb
from ttkbootstrap.constants import BOTH, CENTER, NSEW, PRIMARY, X
from ttkbootstrap.dialogs import Messagebox
from ttkbootstrap.widgets.scrolled import ScrolledFrame

from m_wave.core.utils import (
    FONT,
    H1,
    PAD,
    PAD_X,
    PAD_Y,
)

# local
from m_wave.core.wavepack_frame import WavePackFrame


class LauncherFrame(WavePackFrame):
    """
    WavePack selection screen shown at startup.
    """

    def __init__(self, parent: tkb.Frame, app: App, grid_width: int = 3) -> None:
        super().__init__(
            parent,
            height=360,
            height_min=360,
            width=480,
            width_min=480,
            resizable=(True, True),
        )
        self.app = app
        self.grid_width = grid_width

        self.app.after(500, self._build_ui)

    def _build_ui(self) -> None:
        self.app.update_idletasks()

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

        temp_fnt = font.Font(family="Verdana", size=10)

        max_btn_width = (
            max(temp_fnt.measure(name) for name in self.app.wavepacks) + PAD_X
        )

        for index, (name, info) in enumerate(self.app.wavepacks.items()):
            frame_cls = info[0]
            desc = info[1]
            row = index // self.grid_width
            col = index % self.grid_width

            f = tkb.Frame(self.scroll_frame)
            f.grid(row=row, column=col, padx=PAD_X, pady=PAD_Y, sticky=NSEW)
            f.columnconfigure(0, weight=0, minsize=max_btn_width)
            f.columnconfigure(1, weight=1)

            tkb.Button(
                f,
                text=name,
                command=lambda n=name, fc=frame_cls: self._confirm_and_launch(n, fc),
            ).grid(row=0, column=0, padx=PAD_X, pady=PAD_Y, sticky=NSEW)

            lbl = tkb.Label(
                f,
                text=desc,
                justify="left",
            )
            lbl.grid(row=0, column=1, padx=PAD_X, pady=PAD_Y, sticky=NSEW)

            lbl.bind(
                "<Configure>",
                lambda e, label=lbl: label.config(wraplength=e.width - PAD_X),
            )

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
            self.app.lock_wavepack(name, frame_cls)
