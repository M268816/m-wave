# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
#
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH
"""
The MTL/CMD format helper process. This program takes in file path information
from the user and uses it to either format new Aveva PI tag and configuration
context information into or compare and validate data between csv input data
against design document 20471406.


Functions
---------


Classes
-------
Main
    Application entry point.

Exceptions
----------

"""

# stdlib
import logging
from datetime import datetime

# third party

# local
from src.app.gui import AppWindow
from src.app.metadata import DATETIME_FORMAT
from src.app.paths import LOGS_DIR

# Logging initialization
FORMAT = "%(asctime)s:%(levelname)s:%(filename)s:%(name)s::%(message)s"
LOG_DATETIME = datetime.now().strftime(DATETIME_FORMAT)
LOG_FILENAME = LOGS_DIR / f"{LOG_DATETIME}_general_error.log"

logger = logging.getLogger(__name__)
logging.basicConfig(
    filename=LOG_FILENAME,
    filemode="w",
    format=FORMAT,
    encoding="utf-8",
    level=logging.DEBUG,
)


class Main:
    """
    The entry point that initializes the ttkbootstrap window and instantiates the GUI
    class.

    Attributes
    ----------
    None

    Methods
    -------
    run()
        Starts the tkinter main loop from the Gui class.

    """

    def __init__(self):
        self.app: AppWindow = AppWindow()

    def run(self):
        self.app.run()


if __name__ == "__main__":
    app = Main()
    app.run()
