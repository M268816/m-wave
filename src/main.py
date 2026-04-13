# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
#
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH

# stdlib
import logging
from datetime import datetime

# third party
import ttkbootstrap as tkb

# local
from src.gui import Gui
from src.metadata import DATETIME_FORMAT
from src.paths import LOGS_DIR

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
    A MTL/CMD format helper process. This program takes in file path information
    from the user and uses it to either format new Aveva PI tag and configuration
    context information into or compare and validate data between csv input data
    against design document 20471406.
    """

    def __init__(self):
        self.window = tkb.Window(
            title="λ Workbook Automation & Verification Engine",
        )
        self.gui = Gui(self.window)

    def run(self):
        self.gui.run()


if __name__ == "__main__":
    app = Main()
    app.run()
