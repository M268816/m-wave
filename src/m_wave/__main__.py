# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH
# This tool was created with the help of AI.

# local
from m_wave.core.reporting.debug_log import DebugLog


class Main:
    """
    Application entry point.

    Initializes the GUI application and starts the main loop.
    """

    def __init__(self):
        from m_wave.core.gui import App

        self.app: App = App()
        DebugLog.catch_tk_errors(self.app)

    def run(self):
        self.app.run()


def main():
    """
    Main callable for development, packaging, and console entry points.
    """
    # First thing: start the debug log, so even a crash during startup is recorded.
    DebugLog.setup()
    debug = DebugLog()

    try:
        debug.info("Starting M-WAVE.")
        app = Main()
        app.run()
    except Exception as error:
        debug.error("Unhandled fatal error occurred.", error=error)
        raise


if __name__ == "__main__":
    main()
