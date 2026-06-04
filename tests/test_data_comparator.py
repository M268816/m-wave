"""
Tests for src/data_comparator.py - Data comparison functionality.
"""

import pytest
import pandas as pd
from src.mtl.comparator import DataComparator


class TestDataComparatorShapes:
    """Tests for compare_shapes method."""

    def test_compare_shapes_equal(self, reporting, mock_app_metadata):
        """compare_shapes should detect equal shapes."""
        comparator = DataComparator(reporting, mock_app_metadata)
        df1 = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
        df2 = pd.DataFrame({"A": [5, 6], "B": [7, 8]})

        result = comparator.compare_shapes(df1, df2)

        assert result["shapes_equal"] is True
        assert result["mtl_shape"] == (2, 2)
        assert result["input_shape"] == (2, 2)
        assert result["row_difference"] == 0
        assert result["column_difference"] == 0

    def test_compare_shapes_different_rows(self, reporting, mock_app_metadata):
        """compare_shapes should detect row differences."""
        comparator = DataComparator(reporting, mock_app_metadata)
        df1 = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
        df2 = pd.DataFrame({"A": [1, 2], "B": [4, 5]})

        result = comparator.compare_shapes(df1, df2)

        assert result["shapes_equal"] is False
        assert result["row_difference"] == 1
        assert result["column_difference"] == 0

    def test_compare_shapes_different_columns(self, reporting, mock_app_metadata):
        """compare_shapes should detect column differences."""
        comparator = DataComparator(reporting, mock_app_metadata)
        df1 = pd.DataFrame({"A": [1, 2], "B": [3, 4], "C": [5, 6]})
        df2 = pd.DataFrame({"A": [1, 2], "B": [3, 4]})

        result = comparator.compare_shapes(df1, df2)

        assert result["shapes_equal"] is False
        assert result["row_difference"] == 0
        assert result["column_difference"] == 1

    def test_compare_shapes_empty_dataframe(
        self, reporting, mock_app_metadata, sample_dataframe_empty
    ):
        """compare_shapes should return empty dict for empty df."""
        comparator = DataComparator(reporting, mock_app_metadata)
        result = comparator.compare_shapes(
            sample_dataframe_empty, sample_dataframe_empty
        )

        assert result == {}


class TestDataComparatorRows:
    """Tests for compare_rows method."""

    def test_compare_rows_identical_data(self, reporting, mock_app_metadata):
        """compare_rows should return True for identical data."""
        comparator = DataComparator(reporting, mock_app_metadata)
        df1 = pd.DataFrame(
            {
                "Name": ["Item1", "Item2"],
                "ID": [1, 2],
                "Value": ["100", "200"],
            }
        )
        df2 = pd.DataFrame(
            {
                "Name": ["Item1", "Item2"],
                "ID": [1, 2],
                "Value": ["100", "200"],
            }
        )

        result = comparator.compare_rows(df1, df2)
        assert result is True

    def test_compare_rows_different_data(self, reporting, mock_app_metadata):
        """compare_rows should return True but report differences."""
        comparator = DataComparator(reporting, mock_app_metadata)
        df1 = pd.DataFrame(
            {
                "Name": ["Item1", "Item2"],
                "ID": [1, 2],
                "Value": ["100", "200"],
            }
        )
        df2 = pd.DataFrame(
            {
                "Name": ["Item1", "Item2"],
                "ID": [1, 2],
                "Value": ["100", "999"],  # Different value
            }
        )

        result = comparator.compare_rows(df1, df2)
        assert result is True

    def test_compare_rows_different_row_counts(self, reporting, mock_app_metadata):
        """compare_rows should handle different row counts."""
        comparator = DataComparator(reporting, mock_app_metadata)
        df1 = pd.DataFrame(
            {
                "Name": ["Item1", "Item2", "Item3"],
                "ID": [1, 2, 3],
            }
        )
        df2 = pd.DataFrame(
            {
                "Name": ["Item1", "Item2"],
                "ID": [1, 2],
            }
        )

        result = comparator.compare_rows(df1, df2)
        assert result is True

    def test_compare_rows_empty_mtl(
        self, reporting, mock_app_metadata, sample_dataframe_empty, sample_dataframe
    ):
        """compare_rows should return False for empty MTL."""
        comparator = DataComparator(reporting, mock_app_metadata)
        result = comparator.compare_rows(sample_dataframe_empty, sample_dataframe)

        assert result is False

    def test_compare_rows_empty_input(
        self, reporting, mock_app_metadata, sample_dataframe, sample_dataframe_empty
    ):
        """compare_rows should return False for empty input."""
        comparator = DataComparator(reporting, mock_app_metadata)
        result = comparator.compare_rows(sample_dataframe, sample_dataframe_empty)

        assert result is False


class TestDataComparatorReportShapeDifferences:
    """Tests for _report_shape_differences method."""

    def test_report_shape_equal_dimensions(self, reporting, mock_app_metadata):
        """_report_shape_differences should report match for equal dimensions."""
        comparator = DataComparator(reporting, mock_app_metadata)
        comparator._report_shape_differences(5, 5, "ROW")

        assert any("match" in line.lower() for line in reporting.report_lines)

    def test_report_shape_mtl_larger(self, reporting, mock_app_metadata):
        """_report_shape_differences should report when MTL is larger."""
        comparator = DataComparator(reporting, mock_app_metadata)
        comparator._report_shape_differences(10, 5, "ROW")

        assert any("MTL" in line and "5" in line for line in reporting.report_lines)

    def test_report_shape_input_larger(self, reporting, mock_app_metadata):
        """_report_shape_differences should report when Input is larger."""
        comparator = DataComparator(reporting, mock_app_metadata)
        comparator._report_shape_differences(3, 8, "COLUMN")

        assert any("Input" in line and "5" in line for line in reporting.report_lines)
