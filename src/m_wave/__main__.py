# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
#
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH

# stdlib
import logging
from datetime import datetime

# third party

# local
from m_wave.core.utils import DATETIME_FORMAT
from m_wave.core.paths import PATHS

# Logging initialization
LOG_FORMAT = "%(asctime)s:%(levelname)s:%(filename)s:%(name)s::%(message)s"


def configure_logging():
    """
    Configures application wide logging settings.
    Development:
    m-wave/generated/logs/<timestamp>_general_error.log

    Production:
    exe-folder/logs/<timestamp>_general_error.log
    """
    log_datetime = datetime.now().strftime(DATETIME_FORMAT)
    log_filename = PATHS.logs_dir / f"{log_datetime}_general_error.log"
    logging.basicConfig(
        filename=log_filename,
        filemode="w",
        format=LOG_FORMAT,
        encoding="utf-8",
        level=logging.DEBUG,
    )

class Main:
    """
    Application entry point.
    
    Initializes the GUI application and starts the main loop.
    """

    def __init__(self):
        from m_wave.core.gui import App

        self.app: App = App()

    def run(self):
        self.app.run()

def main():
    """
    Main callable for development, packaging, and console entry points.
    """
    configure_logging()
    logger = logging.getLogger(__name__)

    try:
        logger.info("Starting M-WAVE.")
        app = Main()
        app.run()
    except Exception:
        logger.exception("Unhandled fatal error occurrerd.")
        raise


if __name__ == "__main__":
    main()
