# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH
# This tool was created with the help of AI.

# stdlib
import logging

# local
from m_wave.core.reporting.log_setup import configure_logging


class Main:
    """
    Application entry point.

    Initializes the GUI application and starts the main loop.
    """

    def __init__(self):
        from m_wave.core.gui import App
        from m_wave.core.reporting.log_setup import install_tk_exception_hook

        self.app: App = App()
        install_tk_exception_hook(self.app)

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
        logger.exception("Unhandled fatal error occurred.")
        raise


if __name__ == "__main__":
    main()
