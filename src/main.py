# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
#
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH

# stdlib
import logging
from datetime import datetime

# third party

# local
from src.app.utils import DATETIME_FORMAT
from src.app.paths import PATHS

# Logging initialization
FORMAT = "%(asctime)s:%(levelname)s:%(filename)s:%(name)s::%(message)s"
LOG_DATETIME = datetime.now().strftime(DATETIME_FORMAT)
LOGS_DIR = PATHS.logs_dir
LOG_FILENAME = LOGS_DIR / f"{LOG_DATETIME}_general_error.log"

logger = logging.getLogger(__name__)
logging.basicConfig(
    filename=LOG_FILENAME,
    filemode="w",
    format=FORMAT,
    encoding="utf-8",
    level=logging.DEBUG,
)

# Load last so logging does not break ?
from src.app.gui import AppWindow


class Main:
    """
    The entry point that initializes the ttkbootstrap window and instantiates the GUI
    class.
    """

    def __init__(self):
        self.app: AppWindow = AppWindow()

    def run(self):
        self.app.run()


if __name__ == "__main__":
    app = Main()
    app.run()
