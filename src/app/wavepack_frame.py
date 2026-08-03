# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
#
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH

# stdio

# third party
import ttkbootstrap as tkb

# local
from src.app.wavepack_controller import WavePackController


class WavePackFrame(tkb.Frame):
    """
    Class helper for type assignment.
    """

    def __init__(
        self,
        parent: tkb.Frame,
        height: int,
        height_min: int,
        width: int,
        width_min: int,
        resizable: tuple[bool, bool],
    ) -> None:
        super().__init__(parent)
        self.controller: WavePackController | None = None
        self.height = height
        self.height_min = height_min
        self.width = width
        self.width_min = width_min
        self.resizable = resizable
        self.help_label: str = "Instructions"  # default, override per frame

    @property
    def has_help(self) -> bool:
        """
        Returns True if this frame has overridden show_help.
        AppWindow uses this to decide whether to show the help menu item at all.
        """
        return type(self).show_help is not WavePackFrame.show_help

    def show_help(self) -> None:
        """
        Override in subclasses to display frame-specific help instructions.
        Default is a no-op if not overridden, the help menu item is hidden.
        """
        pass

    @property
    def has_new_menus(self) -> bool:
        """
        Returns True if this frame has overridden get_scrolled_text.
        AppWindow uses this to decide whether to update the report for any
        report configuration changes.
        """
        return type(self).build_menus is not WavePackFrame.build_menus

    def build_menus(self, menubar: tkb.Menu) -> None:
        """
        Override in the subclasses to add WavePack specific menus to the menubar.
        Called by AppWidnow after lock_wavepack()
        """
        pass

    @property
    def has_teardown(self) -> bool:
        """
        Returns true if this frame has overridden on_teardown. AppWindow uses this to
        decide whether to run the teardown logic for WavePackFrames.
        """
        return type(self).on_teardown is not WavePackFrame.on_teardown

    def on_teardown(self) -> None:
        """
        Called by AppWindow before the application closes.
        """
