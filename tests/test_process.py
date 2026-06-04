"""
Tests for src/process.py - orchestration of compare and append workflows.

Strategy
--------
Process.__init__ calls AppMetadata(worksheet_name) and constructs four
collaborator objects (DataExtractor, DataFormatter, DataComparator,
DataAppender).  We patch AppMetadata at the src.process level so that no
real config file is needed, then replace the four collaborators on the
instance directly after construction.  This keeps every test fast and
fully isolated from the filesystem, Excel, and tkinter.

Coverage targets
----------------
  Process.__init__              - collaborators wired correctly
  Process._can_compare()        - True / False paths
  Process.compare_input()       - happy path, every early-exit branch
  Process.append_input()        - happy path, every early-exit branch
"""

import pytest
import pandas as pd
from unittest.mock import MagicMock, patch, call

from src.mtl.process import Process

# ---------------------------------------------------------------------------
# Shared sample data
# ---------------------------------------------------------------------------

SAMPLE_DF = pd.DataFrame(
    {
        "Name": ["Item1", "Item2", "Item3"],
        "ID": [1, 2, 3],
        "Type": ["TypeA", "TypeB", "TypeA"],
        "Value": ["100", "200", "150"],
    }
)

EMPTY_DF = pd.DataFrame()

SHAPE_RESULT = {
    "shapes_equal": True,
    "mtl_shape": (3, 4),
    "input_shape": (3, 4),
    "row_difference": 0,
    "column_difference": 0,
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_window():
    """Minimal tkinter window mock (reuses conftest pattern)."""
    window = MagicMock()
    window.after = MagicMock(side_effect=lambda delay, func: func())
    return window


@pytest.fixture
def reporting(mock_window, tmp_path):
    """Real Reporting instance backed by a temp dir, with modal queue mocked."""
    from src.reporting import Reporting

    report = Reporting(
        parent_window=mock_window,
        output_dir=tmp_path,
        verbose_printing=False,
        populate_report=True,
        populate_log=False,
        use_timestamps=False,
        use_msg_types=False,
    )
    report.create_report("process_test")
    report._queue_modal = MagicMock()
    return report


@pytest.fixture
def mock_metadata():
    """Mock AppMetadata that mimics a comparable ANALYTICS worksheet."""
    from src.metadata import AppMetadata, TableType

    meta = MagicMock(spec=AppMetadata)
    meta.get_worksheet_name.return_value = "TestTable"
    meta.get_table_id.return_value = "TestTableId"
    meta.get_table_type.return_value = TableType.ANALYTICS
    meta.get_table_index_keys.return_value = ["Name", "ID"]
    meta.get_table_filter_keys.return_value = ["Name", "Type"]
    meta.get_table_sort_order.return_value = ["Name"]
    meta.get_table_sort_direction.return_value = [True]
    meta.should_filter_on_keys.return_value = False
    meta.can_compare_worksheet.return_value = True
    meta.get_table_formatting.return_value = {
        "Object Type Order": None,
        "Sort Order": ["Name"],
        "Sort Direction": [True],
    }
    return meta


@pytest.fixture
def process(reporting, mock_metadata):
    """
    A Process instance with AppMetadata patched out and all four
    collaborators replaced with MagicMocks after construction.
    """
    with patch("src.process.AppMetadata", return_value=mock_metadata):
        proc = Process(
            report=reporting,
            filter_string="",
            selected_data_table="TestTable",
            mtl_file_path="/fake/mtl.xlsx",
            input_file_path="/fake/input.csv",
        )

    # Replace collaborators with fresh mocks
    proc.data_extractor = MagicMock()
    proc.data_formatter = MagicMock()
    proc.data_comparator = MagicMock()
    proc.data_appender = MagicMock()
    return proc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _setup_happy_compare(proc):
    """
    Wire all collaborator mocks for a fully successful compare_input() run.
    """
    proc.data_extractor.extract_mtl_table.return_value = SAMPLE_DF.copy()
    proc.data_extractor.extract_input_csv.return_value = SAMPLE_DF.copy()
    proc.data_extractor.could_extract.return_value = True

    proc.data_formatter.format.return_value = SAMPLE_DF.copy()
    proc.data_formatter.could_format.return_value = True
    proc.data_formatter.conform_columns.return_value = (
        SAMPLE_DF.copy(),
        SAMPLE_DF.copy(),
    )
    proc.data_formatter.filter_by_string.return_value = SAMPLE_DF.copy()
    proc.data_formatter.sort.return_value = SAMPLE_DF.copy()

    proc.data_comparator.compare_shapes.return_value = SHAPE_RESULT
    proc.data_comparator.compare_rows.return_value = True


def _setup_happy_append(proc):
    """
    Wire all collaborator mocks for a fully successful append_input() run.
    """
    proc.data_extractor.extract_mtl_table.return_value = SAMPLE_DF.copy()
    proc.data_extractor.extract_input_csv.return_value = SAMPLE_DF.copy()
    proc.data_extractor.could_extract.return_value = True

    proc.data_formatter.format.return_value = SAMPLE_DF.copy()
    proc.data_formatter.could_format.return_value = True
    proc.data_formatter.conform_columns.return_value = (
        SAMPLE_DF.copy(),
        SAMPLE_DF.copy(),
    )

    proc.data_comparator.compare_shapes.return_value = SHAPE_RESULT

    proc.data_appender.upsert.return_value = SAMPLE_DF.copy()


# ===========================================================================
# TestProcessInit
# ===========================================================================


class TestProcessInit:
    """Tests for Process.__init__ — correct wiring of collaborators."""

    def test_collaborators_are_attached(self, process):
        """Process should expose the four collaborator attributes."""
        assert hasattr(process, "data_extractor")
        assert hasattr(process, "data_formatter")
        assert hasattr(process, "data_comparator")
        assert hasattr(process, "data_appender")

    def test_paths_stored(self, process):
        """Process should store file paths and worksheet name."""
        assert process.mtl_file_path == "/fake/mtl.xlsx"
        assert process.input_file_path == "/fake/input.csv"
        assert process.mtl_worksheet_name == "TestTable"

    def test_filter_string_stored(self, reporting, mock_metadata):
        """Process should store the filter string exactly as supplied."""
        with patch("src.process.AppMetadata", return_value=mock_metadata):
            proc = Process(
                report=reporting,
                filter_string="Item*",
                selected_data_table="TestTable",
                mtl_file_path="/fake/mtl.xlsx",
                input_file_path="/fake/input.csv",
            )
        assert proc.filter_string == "Item*"


# ===========================================================================
# TestCanCompare
# ===========================================================================


class TestCanCompare:
    """Tests for Process._can_compare()."""

    def test_returns_true_when_worksheet_supports_compare(self, process, mock_metadata):
        """_can_compare should return True when metadata says can_compare=True."""
        mock_metadata.can_compare_worksheet.return_value = True
        assert process._can_compare() is True

    def test_returns_false_when_worksheet_does_not_support_compare(
        self, process, mock_metadata
    ):
        """_can_compare should return False and report an error when can_compare=False."""
        mock_metadata.can_compare_worksheet.return_value = False
        assert process._can_compare() is False

    def test_reports_error_when_cannot_compare(self, process, mock_metadata):
        """_can_compare should add lines to report_lines when it fails."""
        mock_metadata.can_compare_worksheet.return_value = False
        initial_lines = len(process.report.report_lines)
        process._can_compare()
        assert len(process.report.report_lines) > initial_lines


# ===========================================================================
# TestCompareInputHappyPath
# ===========================================================================


class TestCompareInputHappyPath:
    """Tests for the fully successful compare_input() workflow."""

    def test_returns_true_on_success(self, process):
        """compare_input should return True when all phases succeed."""
        _setup_happy_compare(process)
        assert process.compare_input() is True

    def test_calls_extract_mtl(self, process):
        """compare_input should call extract_mtl_table with the mtl path."""
        _setup_happy_compare(process)
        process.compare_input()
        process.data_extractor.extract_mtl_table.assert_called_once_with(
            "/fake/mtl.xlsx"
        )

    def test_calls_extract_csv(self, process):
        """compare_input should call extract_input_csv with the csv path."""
        _setup_happy_compare(process)
        process.compare_input()
        process.data_extractor.extract_input_csv.assert_called_once_with(
            "/fake/input.csv", ""
        )

    def test_calls_format_twice(self, process):
        """compare_input should call format() for both MTL and input frames."""
        _setup_happy_compare(process)
        process.compare_input()
        assert process.data_formatter.format.call_count == 2

    def test_calls_conform_columns(self, process):
        """compare_input should call conform_columns once."""
        _setup_happy_compare(process)
        process.compare_input()
        process.data_formatter.conform_columns.assert_called_once()

    def test_calls_sort_twice(self, process):
        """compare_input should call sort() for both MTL and input frames."""
        _setup_happy_compare(process)
        process.compare_input()
        assert process.data_formatter.sort.call_count == 2

    def test_calls_compare_shapes(self, process):
        """compare_input should call compare_shapes once."""
        _setup_happy_compare(process)
        process.compare_input()
        process.data_comparator.compare_shapes.assert_called_once()

    def test_calls_compare_rows(self, process):
        """compare_input should call compare_rows once."""
        _setup_happy_compare(process)
        process.compare_input()
        process.data_comparator.compare_rows.assert_called_once()

    def test_saves_report_in_finally(self, process):
        """compare_input should save the report even on a successful run."""
        _setup_happy_compare(process)
        process.compare_input()
        assert process.report.file_path.exists()


# ===========================================================================
# TestCompareInputWithFilter
# ===========================================================================


class TestCompareInputWithFilter:
    """Tests for the filter phase inside compare_input()."""

    def test_filter_by_string_called_when_filter_provided(self, process):
        """compare_input should call filter_by_string on both frames when filter is set."""
        _setup_happy_compare(process)
        process.filter_string = "Item*"
        process.compare_input()
        assert process.data_formatter.filter_by_string.call_count == 2

    def test_filter_by_string_not_called_when_no_filter(self, process):
        """compare_input should skip filter_by_string when filter_string is empty."""
        _setup_happy_compare(process)
        process.filter_string = ""
        process.compare_input()
        process.data_formatter.filter_by_string.assert_not_called()

    def test_filter_on_keys_called_when_metadata_requests_it(
        self, process, mock_metadata
    ):
        """compare_input should call filter_on_keys when should_filter_on_keys=True."""
        _setup_happy_compare(process)
        mock_metadata.should_filter_on_keys.return_value = True
        proc = process
        proc.data_formatter.filter_on_keys.return_value = (
            SAMPLE_DF.copy(),
            SAMPLE_DF.copy(),
        )
        proc.compare_input()
        proc.data_formatter.filter_on_keys.assert_called_once()


# ===========================================================================
# TestCompareInputEarlyExits
# ===========================================================================


class TestCompareInputEarlyExits:
    """Tests for every early-return False branch in compare_input()."""

    def test_returns_false_when_cannot_compare(self, process, mock_metadata):
        """compare_input should return False immediately when _can_compare() is False."""
        mock_metadata.can_compare_worksheet.return_value = False
        result = process.compare_input()
        assert result is False
        process.data_extractor.extract_mtl_table.assert_not_called()

    def test_returns_false_when_extraction_fails(self, process):
        """compare_input should return False when could_extract returns False."""
        _setup_happy_compare(process)
        process.data_extractor.could_extract.return_value = False
        assert process.compare_input() is False

    def test_returns_false_when_format_fails(self, process):
        """compare_input should return False when could_format returns False."""
        _setup_happy_compare(process)
        process.data_formatter.could_format.return_value = False
        assert process.compare_input() is False

    def test_returns_false_when_conform_returns_empty(self, process):
        """compare_input should return False when conform_columns yields empty frames."""
        _setup_happy_compare(process)
        process.data_formatter.conform_columns.return_value = (EMPTY_DF, EMPTY_DF)
        assert process.compare_input() is False

    def test_returns_false_when_sort_returns_empty(self, process):
        """compare_input should return False when sort() returns empty frames."""
        _setup_happy_compare(process)
        process.data_formatter.sort.return_value = EMPTY_DF
        assert process.compare_input() is False

    def test_returns_false_when_compare_shapes_returns_empty_dict(self, process):
        """compare_input should return False when compare_shapes returns {}."""
        _setup_happy_compare(process)
        process.data_comparator.compare_shapes.return_value = {}
        assert process.compare_input() is False

    def test_returns_false_when_compare_rows_fails(self, process):
        """compare_input should return False when compare_rows returns False."""
        _setup_happy_compare(process)
        process.data_comparator.compare_rows.return_value = False
        assert process.compare_input() is False

    def test_returns_false_when_filter_string_empties_frames(self, process):
        """compare_input should return False when filtering produces empty frames."""
        _setup_happy_compare(process)
        process.filter_string = "NoMatch*"
        process.data_formatter.filter_by_string.return_value = EMPTY_DF
        assert process.compare_input() is False

    def test_returns_false_when_filter_on_keys_empties_frames(
        self, process, mock_metadata
    ):
        """compare_input should return False when filter_on_keys produces empty frames."""
        _setup_happy_compare(process)
        mock_metadata.should_filter_on_keys.return_value = True
        process.data_formatter.filter_on_keys.return_value = (EMPTY_DF, EMPTY_DF)
        assert process.compare_input() is False

    def test_saves_report_even_when_extraction_fails(self, process):
        """compare_input finally block should save report even on early exit."""
        _setup_happy_compare(process)
        process.data_extractor.could_extract.return_value = False
        process.compare_input()
        assert process.report.file_path.exists()

    def test_returns_false_on_unexpected_exception(self, process):
        """compare_input should catch unexpected exceptions and return False."""
        process.data_extractor.extract_mtl_table.side_effect = RuntimeError("boom")
        assert process.compare_input() is False

    def test_saves_report_on_unexpected_exception(self, process):
        """compare_input finally block should save report even after an exception."""
        process.data_extractor.extract_mtl_table.side_effect = RuntimeError("boom")
        process.compare_input()
        assert process.report.file_path.exists()


# ===========================================================================
# TestAppendInputHappyPath
# ===========================================================================


class TestAppendInputHappyPath:
    """Tests for the fully successful append_input() workflow."""

    def test_returns_true_on_success(self, process):
        """append_input should return True when all phases succeed."""
        _setup_happy_append(process)
        assert process.append_input() is True

    def test_calls_extract_mtl(self, process):
        """append_input should call extract_mtl_table with the mtl path."""
        _setup_happy_append(process)
        process.append_input()
        process.data_extractor.extract_mtl_table.assert_called_once_with(
            "/fake/mtl.xlsx"
        )

    def test_calls_extract_csv(self, process):
        """append_input should call extract_input_csv with the csv path."""
        _setup_happy_append(process)
        process.append_input()
        process.data_extractor.extract_input_csv.assert_called_once_with(
            "/fake/input.csv", ""
        )

    def test_calls_format_twice(self, process):
        """append_input should call format() for both MTL and input frames."""
        _setup_happy_append(process)
        process.append_input()
        assert process.data_formatter.format.call_count == 2

    def test_calls_conform_columns_with_use_version(self, process):
        """append_input should call conform_columns with use_version=True."""
        _setup_happy_append(process)
        process.append_input()
        process.data_formatter.conform_columns.assert_called_once_with(
            process.data_formatter.format.return_value,
            process.data_formatter.format.return_value,
            use_version=True,
        )

    def test_calls_compare_shapes(self, process):
        """append_input should call compare_shapes once."""
        _setup_happy_append(process)
        process.append_input()
        process.data_comparator.compare_shapes.assert_called_once()

    def test_calls_upsert(self, process):
        """append_input should call upsert on the data_appender."""
        _setup_happy_append(process)
        process.append_input()
        process.data_appender.upsert.assert_called_once()

    def test_calls_export_to_csv(self, process):
        """append_input should export the appended frame to CSV."""
        _setup_happy_append(process)
        process.append_input()
        process.data_appender.export_to_csv.assert_called_once()

    def test_calls_export_to_mtl(self, process):
        """append_input should attempt to write the result back to the MTL file."""
        _setup_happy_append(process)
        process.append_input()
        process.data_appender.export_to_mtl.assert_called_once()

    def test_saves_report_in_finally(self, process):
        """append_input should save the report on a successful run."""
        _setup_happy_append(process)
        process.append_input()
        assert process.report.file_path.exists()


# ===========================================================================
# TestAppendInputEarlyExits
# ===========================================================================


class TestAppendInputEarlyExits:
    """Tests for every early-return False branch in append_input()."""

    def test_returns_false_when_extraction_fails(self, process):
        """append_input should return False when could_extract returns False."""
        _setup_happy_append(process)
        process.data_extractor.could_extract.return_value = False
        assert process.append_input() is False

    def test_returns_false_when_format_fails(self, process):
        """append_input should return False when could_format returns False."""
        _setup_happy_append(process)
        process.data_formatter.could_format.return_value = False
        assert process.append_input() is False

    def test_returns_false_when_conform_returns_empty(self, process):
        """append_input should return False when conform_columns yields empty frames."""
        _setup_happy_append(process)
        process.data_formatter.conform_columns.return_value = (EMPTY_DF, EMPTY_DF)
        assert process.append_input() is False

    def test_returns_false_when_compare_shapes_returns_empty_dict(self, process):
        """append_input should return False when compare_shapes returns {}."""
        _setup_happy_append(process)
        process.data_comparator.compare_shapes.return_value = {}
        assert process.append_input() is False

    def test_returns_false_when_upsert_returns_empty(self, process):
        """append_input should return False when upsert returns an empty DataFrame."""
        _setup_happy_append(process)
        process.data_appender.upsert.return_value = EMPTY_DF
        assert process.append_input() is False

    def test_does_not_export_when_upsert_fails(self, process):
        """append_input should not call export_to_csv or export_to_mtl if upsert fails."""
        _setup_happy_append(process)
        process.data_appender.upsert.return_value = EMPTY_DF
        process.append_input()
        process.data_appender.export_to_csv.assert_not_called()
        process.data_appender.export_to_mtl.assert_not_called()

    def test_saves_report_even_when_extraction_fails(self, process):
        """append_input finally block should save report even on early exit."""
        _setup_happy_append(process)
        process.data_extractor.could_extract.return_value = False
        process.append_input()
        assert process.report.file_path.exists()

    def test_returns_false_on_unexpected_exception(self, process):
        """append_input should catch unexpected exceptions and return False."""
        process.data_extractor.extract_mtl_table.side_effect = RuntimeError("boom")
        assert process.append_input() is False

    def test_saves_report_on_unexpected_exception(self, process):
        """append_input finally block should save report even after an exception."""
        process.data_extractor.extract_mtl_table.side_effect = RuntimeError("boom")
        process.append_input()
        assert process.report.file_path.exists()
