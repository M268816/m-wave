# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH
# This tool was created with the help of AI.


from collections.abc import Callable


class UIEvent:
    """
    Base class for a UIEvent.
    """


def ignore_ui_event(event: UIEvent) -> None:
    """
    Default event bus used when no UI is attached.
    """


UIEventSink = Callable[[UIEvent], None]
