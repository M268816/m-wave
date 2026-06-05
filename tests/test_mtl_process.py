# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved

"""
Tests for src/mtl/process.py -- Process orchestration.

All four collaborators (DataExtractor, DataFormatter, DataComparator,
DataAppender) are replaced with MagicMocks after construction, so no
filesystem, Excel, or GUI interaction occurs.
No GUI dependency.
"""

import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from src.mtl.process import Process


SAMPLE_DF = pd.DataFrame(
    {
        "Name": ["Item1", "Item2", "Item3"],
        "ID": [1, 2, 3],
        "Type": ["TypeA", "TypeB", "TypeA"],
        "Value": ["100", "200", "150"],
    }
)
EMPTY_DF = pd.DataFrame()
SHAPE_OK = {
    "shapes_equal": True,
    "mtl_shape": (3, 4),
    "input_shape": (3, 4),
    "row_difference": 0,
    "column_difference": 0,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _happy_compare(proc):
    proc.data_extractor.extract_mtl_table.return_value = SAMPLE_DF.copy()
    proc.data_extractor.extract_input_csv.return_value = SAMPLE_DF.copy()
    proc.data_extractor.could_extract.return_value = True
    proc.data_formatter.format.return_value = SAMPLE_DF.copy()
    proc.data_formatter.could_format.return_value = True
    proc.data_formatter.conform_columns.return_value = (SAMPLE_DF.copy(), SAMPLE_DF.copy())
    proc.data_formatter.filter_by_string.return_value = SAMPLE_DF.copy()
    proc.data_formatter.sort.return_value = SAMPLE_DF.copy()
    proc.data_comparator.compare_shapes.return_value = SHAPE_OK
    proc.data_comparator.compare_rows.return_value = True


def _happy_append(proc):
    proc.data_extractor.extract_mtl_table.return_value = SAMPLE_DF.copy()
    proc.data_extractor.extract_input_csv.return_value = SAMPLE_DF.copy()
    proc.data_extractor.could_extract.return_value = True
    proc.data_formatter.format.return_value = SAMPLE_DF.copy()
    proc.data_formatter.could_format.return_value = True
    proc.data_formatter.conform_columns.return_value = (SAMPLE_DF.copy(), SAMPLE_DF.copy())
    proc.data_formatter.filter_by_string.return_value = SAMPLE_DF.copy()
    proc.data_comparator.compare_shapes.return_value = SHAPE_OK
    proc.data_appender.upsert.return_value = SAMPLE_DF.copy()


# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------

class TestProcessInit:

    def test_collaborators_attached(self, process):
        for attr in ("data_extractor", "data_formatter", "data_comparator", "data_appender"):
            assert hasattr(process, attr)

    def test_paths_stored(self, process):
        assert process.mtl_file_path == "/fake/mtl.xlsx"
        assert process.input_file_path == "/fake/input.csv"
        assert process.mtl_worksheet_name == "TestTable"

    def test_filter_string_stored(self, reporting, mock_metadata):
        with patch("src.mtl.process.AppMetadata", return_value=mock_metadata):
            proc = Process(
                report=reporting,
                filter_string="Item*",
                selected_data_table="TestTable",
                mtl_file_path="/fake/mtl.xlsx",
                input_file_path="/fake/input.csv",
            )
        assert proc.filter_string == "Item*"

    def test_report_stored(self, reporting, mock_metadata):
        with patch("src.mtl.process.AppMetadata", return_value=mock_metadata):
            proc = Process(
                report=reporting,
                filter_string="",
                selected_data_table="TestTable",
                mtl_file_path="/fake/mtl.xlsx",
                input_file_path="/fake/input.csv",
            )
        assert proc.report is reporting


# ---------------------------------------------------------------------------
# _can_compare
# ---------------------------------------------------------------------------

class TestCanCompare:

    def test_returns_true_when_allowed(self, process, mock_metadata):
        mock_metadata.can_compare_worksheet.return_value = True
        assert process._can_compare() is True

    def test_returns_false_when_not_allowed(self, process, mock_metadata):
        mock_metadata.can_compare_worksheet.return_value = False
        assert process._can_compare() is False

    def test_logs_error_when_cannot_compare(self, process, mock_metadata):
        mock_metadata.can_compare_worksheet.return_value = False
        before = len(process.report.report_lines)
        process._can_compare()
        assert len(process.report.report_lines) > before


# ---------------------------------------------------------------------------
# compare_input -- happy path
# ---------------------------------------------------------------------------

class TestCompareInputHappyPath:

    def test_returns_true(self, process):
        _happy_compare(process)
        assert process.compare_input() is True

    def test_calls_extract_mtl(self, process):
        _happy_compare(process)
        process.compare_input()
        process.data_extractor.extract_mtl_table.assert_called_once_with("/fake/mtl.xlsx")

    def test_calls_extract_csv(self, process):
        _happy_compare(process)
        process.compare_input()
        process.data_extractor.extract_input_csv.assert_called_once_with("/fake/input.csv", "")

    def test_calls_format_twice(self, process):
        _happy_compare(process)
        process.compare_input()
        assert process.data_formatter.format.call_count == 2

    def test_calls_conform_columns(self, process):
        _happy_compare(process)
        process.compare_input()
        process.data_formatter.conform_columns.assert_called_once()

    def test_calls_sort_twice(self, process):
        _happy_compare(process)
        process.compare_input()
        assert process.data_formatter.sort.call_count == 2

    def test_calls_compare_shapes(self, process):
        _happy_compare(process)
        process.compare_input()
        process.data_comparator.compare_shapes.assert_called_once()

    def test_calls_compare_rows(self, process):
        _happy_compare(process)
        process.compare_input()
        process.data_comparator.compare_rows.assert_called_once()

    def test_saves_report(self, process):
        _happy_compare(process)
        process.compare_input()
        assert process.report.file_path.exists()


# ---------------------------------------------------------------------------
# compare_input -- early exits
# ---------------------------------------------------------------------------

class TestCompareInputEarlyExits:

    def test_cannot_compare_stops_immediately(self, process, mock_metadata):
        mock_metadata.can_compare_worksheet.return_value = False
        assert process.compare_input() is False
        process.data_extractor.extract_mtl_table.assert_not_called()

    def test_extraction_failure_stops(self, process):
        process.data_extractor.extract_mtl_table.return_value = SAMPLE_DF.copy()
        process.data_extractor.extract_input_csv.return_value = SAMPLE_DF.copy()
        process.data_extractor.could_extract.return_value = False
        assert process.compare_input() is False
        process.data_formatter.format.assert_not_called()

    def test_format_failure_stops(self, process):
        process.data_extractor.extract_mtl_table.return_value = SAMPLE_DF.copy()
        process.data_extractor.extract_input_csv.return_value = SAMPLE_DF.copy()
        process.data_extractor.could_extract.return_value = True
        process.data_formatter.format.return_value = SAMPLE_DF.copy()
        process.data_formatter.could_format.return_value = False
        assert process.compare_input() is False
        process.data_formatter.conform_columns.assert_not_called()

    def test_conform_empty_stops(self, process):
        process.data_extractor.extract_mtl_table.return_value = SAMPLE_DF.copy()
        process.data_extractor.extract_input_csv.return_value = SAMPLE_DF.copy()
        process.data_extractor.could_extract.return_value = True
        process.data_formatter.format.return_value = SAMPLE_DF.copy()
        process.data_formatter.could_format.return_value = True
        process.data_formatter.conform_columns.return_value = (EMPTY_DF, EMPTY_DF)
        assert process.compare_input() is False

    def test_sort_empty_stops(self, process):
        process.data_extractor.extract_mtl_table.return_value = SAMPLE_DF.copy()
        process.data_extractor.extract_input_csv.return_value = SAMPLE_DF.copy()
        process.data_extractor.could_extract.return_value = True
        process.data_formatter.format.return_value = SAMPLE_DF.copy()
        process.data_formatter.could_format.return_value = True
        process.data_formatter.conform_columns.return_value = (SAMPLE_DF.copy(), SAMPLE_DF.copy())
        process.data_formatter.sort.return_value = EMPTY_DF
        assert process.compare_input() is False
        process.data_comparator.compare_shapes.assert_not_called()

    def test_empty_shape_result_stops(self, process):
        _happy_compare(process)
        process.data_comparator.compare_shapes.return_value = {}
        assert process.compare_input() is False
        process.data_comparator.compare_rows.assert_not_called()

    def test_compare_rows_false_stops(self, process):
        _happy_compare(process)
        process.data_comparator.compare_rows.return_value = False
        assert process.compare_input() is False


# ---------------------------------------------------------------------------
# compare_input -- filter branches
# ---------------------------------------------------------------------------

class TestCompareInputFilter:

    def test_filter_string_calls_filter_twice(self, process):
        _happy_compare(process)
        process.filter_string = "Item*"
        process.compare_input()
        assert process.data_formatter.filter_by_string.call_count == 2

    def test_no_filter_skips_filter_call(self, process):
        _happy_compare(process)
        process.filter_string = ""
        process.compare_input()
        process.data_formatter.filter_by_string.assert_not_called()

    def test_filter_empty_result_stops(self, process):
        _happy_compare(process)
        process.filter_string = "NoMatch*"
        process.data_formatter.filter_by_string.return_value = EMPTY_DF
        assert process.compare_input() is False

    def test_filter_on_keys_called_when_metadata_says_so(self, process, mock_metadata):
        _happy_compare(process)
        mock_metadata.should_filter_on_keys.return_value = True
        process.data_formatter.filter_on_keys.return_value = (SAMPLE_DF.copy(), SAMPLE_DF.copy())
        process.compare_input()
        process.data_formatter.filter_on_keys.assert_called_once()

    def test_filter_on_keys_empty_stops(self, process, mock_metadata):
        _happy_compare(process)
        mock_metadata.should_filter_on_keys.return_value = True
        process.data_formatter.filter_on_keys.return_value = (EMPTY_DF, EMPTY_DF)
        assert process.compare_input() is False


# ---------------------------------------------------------------------------
# append_input -- happy path
# ---------------------------------------------------------------------------

class TestAppendInputHappyPath:

    def test_returns_true(self, process):
        _happy_append(process)
        assert process.append_input() is True

    def test_calls_extract_mtl(self, process):
        _happy_append(process)
        process.append_input()
        process.data_extractor.extract_mtl_table.assert_called_once_with("/fake/mtl.xlsx")

    def test_calls_extract_csv(self, process):
        _happy_append(process)
        process.append_input()
        process.data_extractor.extract_input_csv.assert_called_once_with("/fake/input.csv", "")

    def test_calls_format_twice(self, process):
        _happy_append(process)
        process.append_input()
        assert process.data_formatter.format.call_count == 2

    def test_calls_conform_columns_with_use_version(self, process):
        _happy_append(process)
        process.append_input()
        process.data_formatter.conform_columns.assert_called_once_with(
            process.data_formatter.format.return_value,
            process.data_formatter.format.return_value,
            use_version=True,
        )

    def test_calls_upsert(self, process):
        _happy_append(process)
        process.append_input()
        process.data_appender.upsert.assert_called_once()

    def test_calls_export_to_csv(self, process):
        _happy_append(process)
        process.append_input()
        process.data_appender.export_to_csv.assert_called_once_with(
            process.data_appender.upsert.return_value
        )

    def test_calls_export_to_mtl(self, process):
        _happy_append(process)
        process.append_input()
        process.data_appender.export_to_mtl.assert_called_once_with(
            process.data_appender.upsert.return_value, "/fake/mtl.xlsx"
        )

    def test_saves_report(self, process):
        _happy_append(process)
        process.append_input()
        assert process.report.file_path.exists()


# ---------------------------------------------------------------------------
# append_input -- early exits
# ---------------------------------------------------------------------------

class TestAppendInputEarlyExits:

    def test_extraction_failure_stops(self, process):
        process.data_extractor.extract_mtl_table.return_value = SAMPLE_DF.copy()
        process.data_extractor.extract_input_csv.return_value = SAMPLE_DF.copy()
        process.data_extractor.could_extract.return_value = False
        assert process.append_input() is False
        process.data_formatter.format.assert_not_called()

    def test_format_failure_stops(self, process):
        process.data_extractor.extract_mtl_table.return_value = SAMPLE_DF.copy()
        process.data_extractor.extract_input_csv.return_value = SAMPLE_DF.copy()
        process.data_extractor.could_extract.return_value = True
        process.data_formatter.format.return_value = SAMPLE_DF.copy()
        process.data_formatter.could_format.return_value = False
        assert process.append_input() is False
        process.data_formatter.conform_columns.assert_not_called()

    def test_conform_empty_stops(self, process):
        process.data_extractor.extract_mtl_table.return_value = SAMPLE_DF.copy()
        process.data_extractor.extract_input_csv.return_value = SAMPLE_DF.copy()
        process.data_extractor.could_extract.return_value = True
        process.data_formatter.format.return_value = SAMPLE_DF.copy()
        process.data_formatter.could_format.return_value = True
        process.data_formatter.conform_columns.return_value = (EMPTY_DF, EMPTY_DF)
        assert process.append_input() is False

    def test_empty_shape_result_stops(self, process):
        _happy_append(process)
        process.data_comparator.compare_shapes.return_value = {}
        assert process.append_input() is False
        process.data_appender.upsert.assert_not_called()

    def test_upsert_empty_stops(self, process):
        _happy_append(process)
        process.data_appender.upsert.return_value = EMPTY_DF
        assert process.append_input() is False
        process.data_appender.export_to_csv.assert_not_called()


# ---------------------------------------------------------------------------
# append_input -- filter branch
# ---------------------------------------------------------------------------

class TestAppendInputFilter:

    def test_filter_calls_filter_once_on_input(self, process):
        _happy_append(process)
        process.filter_string = "Item*"
        process.append_input()
        assert process.data_formatter.filter_by_string.call_count == 1

    def test_no_filter_skips_filter_call(self, process):
        _happy_append(process)
        process.filter_string = ""
        process.append_input()
        process.data_formatter.filter_by_string.assert_not_called()

    def test_filter_empty_result_stops(self, process):
        _happy_append(process)
        process.filter_string = "NoMatch*"
        process.data_formatter.filter_by_string.return_value = EMPTY_DF
        assert process.append_input() is False
