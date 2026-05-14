"""
Tests for src/reporting.py - Reporting and logging functionality.
"""

import pytest
from pathlib import Path
from datetime import datetime
from src.reporting import Reporting, LogConfig


class TestReportingInitialization:
    """Tests for Reporting class initialization."""

    def test_reporting_creation(self, mock_window, temp_report_dir):
        """Reporting should initialize with required parameters."""
        report = Reporting(
            parent_window=mock_window,
            output_dir=temp_report_dir,
            verbose_printing=False,
        )
        assert report.parent_window is mock_window
        assert report.output_dir == temp_report_dir
        assert report.verbose is False

    def test_reporting_defaults(self, mock_window, temp_report_dir):
        """Reporting should have expected default values."""
        report = Reporting(mock_window, temp_report_dir)
        assert report.use_timestamps is True
        assert report.use_msg_types is True
        assert report.report_lines == []

    def test_reporting_with_custom_timestamp(self, mock_window, temp_report_dir):
        """Reporting should accept a custom timestamp."""
        custom_time = datetime(2024, 1, 1, 12, 0, 0)
        report = Reporting(
            mock_window,
            temp_report_dir,
            timestamp=custom_time,
        )
        assert custom_time in str(report.timestamp)


class TestReportingCreateReport:
    """Tests for create_report method."""

    def test_create_report_sets_name(self, reporting):
        """create_report should set the report name."""
        reporting.create_report("TestReport")
        assert reporting.name == "TestReport"

    def test_create_report_creates_folder(self, reporting):
        """create_report should create the report folder."""
        reporting.create_report("FolderTest")
        assert reporting.report_folder.exists()

    def test_create_report_cleans_name(self, reporting):
        """create_report should clean the name of special characters."""
        reporting.create_report("*Test Report*")
        assert reporting.cleaned_name == "Test_Report"

    def test_create_report_empty_name_becomes_no_filter(self, reporting):
        """create_report with empty name should use 'No_Filter'."""
        reporting.create_report("")
        assert reporting.name == "No_Filter"

    def test_create_report_resets_lines(self, reporting):
        """create_report should reset report_lines."""
        reporting.report_lines = ["old line"]
        reporting.create_report("NewReport")
        assert reporting.report_lines == []


class TestReportingLogMethods:
    """Tests for logging methods (info, warning, error, etc)."""

    def test_info_adds_to_report_lines(self, reporting):
        """info() should add messages to report_lines."""
        reporting.info("Test message")
        assert len(reporting.report_lines) > 0
        assert "Test message" in reporting.report_lines[-1]

    def test_warning_adds_to_report_lines(self, reporting):
        """warning() should add messages to report_lines."""
        reporting.warning("Warning message")
        assert len(reporting.report_lines) > 0
        assert "Warning message" in reporting.report_lines[-1]

    def test_error_adds_to_report_lines(self, reporting):
        """error() should add messages to report_lines."""
        reporting.error("Error message")
        assert len(reporting.report_lines) > 0
        assert "Error message" in reporting.report_lines[-1]

    def test_debug_adds_to_report_lines(self, reporting):
        """debug() should add messages to report_lines."""
        reporting.debug("Debug message")
        assert len(reporting.report_lines) > 0
        assert "Debug message" in reporting.report_lines[-1]

    def test_exception_adds_to_report_lines(self, reporting):
        """exception() should add messages to report_lines."""
        reporting.exception("Exception message")
        assert len(reporting.report_lines) > 0
        assert "Exception message" in reporting.report_lines[-1]

    def test_critical_adds_to_report_lines(self, reporting):
        """critical() should add messages to report_lines."""
        reporting.critical("Critical message")
        assert len(reporting.report_lines) > 0
        assert "Critical message" in reporting.report_lines[-1]


class TestReportingTimestamps:
    """Tests for timestamp behavior."""

    def test_report_lines_include_timestamps_when_enabled(
        self, mock_window, temp_report_dir
    ):
        """Report lines should include timestamps when use_timestamps=True."""
        report = Reporting(mock_window, temp_report_dir, use_timestamps=True)
        report.create_report("Test")
        report.info("Message")
        assert any(":" in line for line in report.report_lines)

    def test_report_lines_exclude_timestamps_when_disabled(
        self, mock_window, temp_report_dir
    ):
        """Report lines should exclude timestamps when use_timestamps=False."""
        report = Reporting(mock_window, temp_report_dir, use_timestamps=False)
        report.create_report("Test")
        report.info("Message")
        # Without timestamps, info lines should be plain
        assert any("Message" in line for line in report.report_lines)


class TestReportingFormatting:
    """Tests for formatting helper methods."""

    def test_title_creates_box(self, reporting):
        """title() should create a formatted title box."""
        reporting.title("My Title")
        assert any("╔" in line for line in report.report_lines)
        assert any("╗" in line for line in report.report_lines)
        assert any("My Title" in line for line in report.report_lines)

    def test_subtitle_creates_light_box(self, reporting):
        """subtitle() should create a light formatted box."""
        reporting.subtitle("My Subtitle")
        assert any("┌" in line for line in report.report_lines)
        assert any("┐" in line for line in report.report_lines)

    def test_divider_creates_full_width_line(self, reporting):
        """divider() should create a full-width heavy line."""
        reporting.divider()
        assert any("═" * 10 in line for line in report.report_lines)

    def test_separator_creates_light_line(self, reporting):
        """separator() should create a light divider."""
        reporting.separator()
        assert any("─" * 10 in line for line in report.report_lines)


class TestReportingSaveReport:
    """Tests for save_report method."""

    def test_save_report_creates_file(self, reporting):
        """save_report() should create a log file."""
        reporting.info("Test message")
        reporting.save_report()
        assert reporting.file_path.exists()

    def test_saved_report_contains_messages(self, reporting):
        """Saved report file should contain logged messages."""
        reporting.info("Test message for file")
        reporting.save_report()
        content = reporting.file_path.read_text()
        assert "Test message for file" in content

    def test_save_report_without_create_report_raises_error(
        self, mock_window, temp_report_dir
    ):
        """save_report() without create_report() should raise RuntimeError."""
        report = Reporting(mock_window, temp_report_dir)
        with pytest.raises(RuntimeError):
            report.save_report()
