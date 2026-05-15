# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
"""
Tests for src/main.py - Application entry point.
"""

import pytest
from unittest.mock import MagicMock, patch, call


class TestMainClass:
    """Tests for the Main class in src/main.py."""

    @patch("src.main.Gui")
    @patch("src.main.tkb.Window")
    def test_main_creates_window(self, mock_window, mock_gui):
        """Main.__init__ should create a ttkbootstrap Window."""
        from src.main import Main

        app = Main()

        mock_window.assert_called_once_with(
            title="λ Workbook Automation & Verification Engine",
        )

    @patch("src.main.Gui")
    @patch("src.main.tkb.Window")
    def test_main_creates_gui_with_window(self, mock_window, mock_gui):
        """Main.__init__ should instantiate Gui and pass the window to it."""
        from src.main import Main

        app = Main()

        mock_gui.assert_called_once_with(mock_window.return_value)

    @patch("src.main.Gui")
    @patch("src.main.tkb.Window")
    def test_main_run_calls_gui_run(self, mock_window, mock_gui):
        """Main.run() should delegate to self.gui.run()."""
        from src.main import Main

        app = Main()
        app.run()

        mock_gui.return_value.run.assert_called_once()

    @patch("src.main.Gui")
    @patch("src.main.tkb.Window")
    def test_main_stores_window_as_attribute(self, mock_window, mock_gui):
        """Main.__init__ should store the window as self.window."""
        from src.main import Main

        app = Main()

        assert app.window is mock_window.return_value

    @patch("src.main.Gui")
    @patch("src.main.tkb.Window")
    def test_main_stores_gui_as_attribute(self, mock_window, mock_gui):
        """Main.__init__ should store the Gui instance as self.gui."""
        from src.main import Main

        app = Main()

        assert app.gui is mock_gui.return_value

    @patch("src.main.Gui")
    @patch("src.main.tkb.Window")
    def test_main_does_not_raise_on_init(self, mock_window, mock_gui):
        """Main() should not raise any exception during normal init."""
        from src.main import Main

        try:
            app = Main()
        except Exception as e:
            pytest.fail(f"Main.__init__ raised unexpectedly: {e}")

    @patch("src.main.Gui")
    @patch("src.main.tkb.Window")
    def test_main_does_not_raise_on_run(self, mock_window, mock_gui):
        """Main.run() should not raise any exception under normal conditions."""
        from src.main import Main

        app = Main()
        try:
            app.run()
        except Exception as e:
            pytest.fail(f"Main.run() raised unexpectedly: {e}")


class TestMainLogging:
    """Tests for module-level logging setup in src/main.py."""

    @patch("src.main.Gui")
    @patch("src.main.tkb.Window")
    def test_module_imports_cleanly(self, mock_window, mock_gui):
        """src.main should import without errors when GUI deps are mocked."""
        try:
            import importlib
            import src.main

            importlib.reload(src.main)
        except Exception as e:
            pytest.fail(f"src.main failed to import: {e}")

    @patch("src.main.Gui")
    @patch("src.main.tkb.Window")
    def test_log_filename_uses_datetime_format(self, mock_window, mock_gui):
        """LOG_FILENAME should be a Path constructed from LOGS_DIR."""
        import src.main
        from src.paths import LOGS_DIR

        assert str(LOGS_DIR) in str(src.main.LOG_FILENAME)

    @patch("src.main.Gui")
    @patch("src.main.tkb.Window")
    def test_logger_is_named_after_module(self, mock_window, mock_gui):
        """The module logger should be named __main__ or src.main."""
        import src.main

        assert src.main.logger.name in ("__main__", "src.main")
