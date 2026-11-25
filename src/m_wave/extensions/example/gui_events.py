# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH
# This tool was created with the help of AI.

from dataclasses import dataclass

from m_wave.core.gui_events import UIEvent


@dataclass(frozen=True)
class EventExample(UIEvent):
    """
    Processor event when the status ui changes.
    """

    message: str


@dataclass(frozen=True)
class EventExampleTwo(UIEvent):
    """
    Unused, but an example of multiple event types.
    """

    progress: int
    button_state: str
