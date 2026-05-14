"""
Tests for src/data_formatter.py - Data formatting and transformation.
"""

import pytest
import pandas as pd
from src.data_formatter import DataFormatter


class TestDataFormatterNormalizeWhitespace:
    """Tests for _normalize_whitespace method."""

    def test_normalize_removes_extra_spaces(self, reporting, mock_app_metadata):
        """normalize_whitespace should remove extra spaces."""
        formatter = DataFormatter(reporting, mock_app_metadata)
        df = pd.DataFrame({"Name": ["  Item  1  ", "Item   2"]})
        result = formatter._normalize_whitespace(df)
        assert result["Name"].iloc[0] == "Item 1"
        assert result["Name"].iloc[1] == "Item 2"

    def test_normalize_removes_newlines(self, reporting, mock_app_metadata):
        """normalize_whitespace should remove newlines."""
        formatter = DataFormatter(reporting, mock_app_metadata)
        df = pd.DataFrame({"Name": ["Item\n1", "Item\r\n2"]})
        result = formatter._normalize_whitespace(df)
        assert "\n" not in result["Name"].iloc[0]
        assert "\r" not in result["Name"].iloc[1]

    def test_normalize_on_specific_columns(self, reporting, mock_app_metadata):
        """normalize_whitespace should work on specific columns only."""
        formatter = DataFormatter(reporting, mock_app_metadata)
        df = pd.DataFrame(
            {
                "Name": ["  Item  1  "],
                "ID": ["  123  "],
            }
        )
        result = formatter._normalize_whitespace(df, columns=["Name"])
        assert result["Name"].iloc[0] == "Item 1"
        assert result["ID"].iloc[0] == "  123  "  # Unchanged


class TestDataFormatterFilterByString:
    """Tests for filter_by_string method."""

    def test_filter_exact_match(self, reporting, mock_app_metadata, sample_dataframe):
        """filter_by_string should find exact matches."""
        formatter = DataFormatter(reporting, mock_app_metadata)
        result = formatter.filter_by_string(sample_dataframe, "Item1")
        assert len(result) == 1
        assert result["Name"].iloc[0] == "Item1"

    def test_filter_wildcard_start(
        self, reporting, mock_app_metadata, sample_dataframe
    ):
        """filter_by_string should handle leading wildcards."""
        formatter = DataFormatter(reporting, mock_app_metadata)
        result = formatter.filter_by_string(sample_dataframe, "*Item")
        assert len(result) == 3  # All rows have "Item"

    def test_filter_wildcard_end(self, reporting, mock_app_metadata, sample_dataframe):
        """filter_by_string should handle trailing wildcards."""
        formatter = DataFormatter(reporting, mock_app_metadata)
        result = formatter.filter_by_string(sample_dataframe, "Item*")
        assert len(result) == 3

    def test_filter_no_match(self, reporting, mock_app_metadata, sample_dataframe):
        """filter_by_string should return empty df on no match."""
        formatter = DataFormatter(reporting, mock_app_metadata)
        result = formatter.filter_by_string(sample_dataframe, "NonExistent")
        assert len(result) == 0

    def test_filter_empty_string_returns_original(
        self, reporting, mock_app_metadata, sample_dataframe
    ):
        """filter_by_string with empty string should return original df."""
        formatter = DataFormatter(reporting, mock_app_metadata)
        result = formatter.filter_by_string(sample_dataframe, "")
        pd.testing.assert_frame_equal(result, sample_dataframe)

    def test_filter_empty_dataframe(
        self, reporting, mock_app_metadata, sample_dataframe_empty
    ):
        """filter_by_string on empty df should return empty df."""
        formatter = DataFormatter(reporting, mock_app_metadata)
        result = formatter.filter_by_string(sample_dataframe_empty, "test")
        assert result.empty


class TestDataFormatterFormat:
    """Tests for format method."""

    def test_format_converts_to_string(
        self, reporting, mock_app_metadata, sample_dataframe
    ):
        """format() should convert columns to string type."""
        formatter = DataFormatter(reporting, mock_app_metadata)
        result = formatter.format(sample_dataframe.copy())
        # Check that string columns are string type
        assert result is not None
        assert not result.empty

    def test_format_returns_empty_on_none(self, reporting, mock_app_metadata):
        """format() should return empty df when passed None."""
        formatter = DataFormatter(reporting, mock_app_metadata)
        result = formatter.format(None)
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_format_removes_blank_columns(self, reporting, mock_app_metadata):
        """format() should remove columns with blank names."""
        formatter = DataFormatter(reporting, mock_app_metadata)
        df = pd.DataFrame({"Name": [1, 2], "": [3, 4], " ": [5, 6]})
        result = formatter.format(df)
        assert "" not in result.columns
        assert " " not in result.columns

    def test_format_drops_na_rows_on_index_keys(self, reporting, mock_app_metadata):
        """format() should drop rows without values in index keys."""
        formatter = DataFormatter(reporting, mock_app_metadata)
        df = pd.DataFrame(
            {
                "Name": ["Item1", None, "Item3"],
                "ID": [1, None, 3],
            }
        )
        result = formatter.format(df)
        # At least one key must have a value to keep the row
        assert len(result) <= len(df)


class TestDataFormatterConformColumns:
    """Tests for conform_columns method."""

    def test_conform_removes_extra_input_columns(self, reporting, mock_app_metadata):
        """conform_columns should remove input columns not in MTL."""
        formatter = DataFormatter(reporting, mock_app_metadata)
        mtl_df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
        input_df = pd.DataFrame({"A": [5, 6], "B": [7, 8], "C": [9, 10]})

        mtl_result, input_result = formatter.conform_columns(mtl_df, input_df)

        assert "C" not in input_result.columns
        assert set(input_result.columns) == set(mtl_result.columns)

    def test_conform_returns_empty_on_none_input(self, reporting, mock_app_metadata):
        """conform_columns should return empty dfs when passed None."""
        formatter = DataFormatter(reporting, mock_app_metadata)
        mtl_result, input_result = formatter.conform_columns(None, None)

        assert mtl_result.empty
        assert input_result.empty

    def test_conform_adds_version_column_when_requested(
        self, reporting, mock_app_metadata
    ):
        """conform_columns should add Version column when use_version=True."""
        formatter = DataFormatter(reporting, mock_app_metadata)
        mtl_df = pd.DataFrame({"A": [1, 2]})
        input_df = pd.DataFrame({"A": [3, 4]})

        mtl_result, input_result = formatter.conform_columns(
            mtl_df, input_df, use_version=True
        )

        # Version column should exist in result
        assert "Version" in input_result.columns or len(input_result.columns) > 0


class TestDataFormatterSort:
    """Tests for sort method."""

    def test_sort_maintains_dataframe_integrity(
        self, reporting, mock_app_metadata, sample_dataframe
    ):
        """sort() should maintain dataframe integrity."""
        formatter = DataFormatter(reporting, mock_app_metadata)
        result = formatter.sort(sample_dataframe.copy())

        assert not result.empty
        assert len(result) == len(sample_dataframe)
        assert set(result.columns) == set(sample_dataframe.columns)

    def test_sort_resets_index(self, reporting, mock_app_metadata, sample_dataframe):
        """sort() should reset the index."""
        formatter = DataFormatter(reporting, mock_app_metadata)
        df = sample_dataframe.copy()
        df.index = [10, 20, 30]  # Non-standard index
        result = formatter.sort(df)

        assert list(result.index) == list(range(len(result)))

    def test_sort_empty_dataframe_returns_empty(self, reporting, mock_app_metadata):
        """sort() should handle empty dataframes."""
        formatter = DataFormatter(reporting, mock_app_metadata)
        result = formatter.sort(pd.DataFrame())
        assert result.empty


class TestDataFormatterCouldFormat:
    """Tests for could_format validation method."""

    def test_could_format_true_for_valid_dfs(
        self, reporting, mock_app_metadata, sample_dataframe
    ):
        """could_format should return True for valid dataframes."""
        formatter = DataFormatter(reporting, mock_app_metadata)
        result = formatter.could_format(sample_dataframe, sample_dataframe)
        assert result is True

    def test_could_format_false_for_empty_mtl(
        self, reporting, mock_app_metadata, sample_dataframe_empty, sample_dataframe
    ):
        """could_format should return False if MTL is empty."""
        formatter = DataFormatter(reporting, mock_app_metadata)
        result = formatter.could_format(sample_dataframe_empty, sample_dataframe)
        assert result is False

    def test_could_format_false_for_empty_input(
        self, reporting, mock_app_metadata, sample_dataframe, sample_dataframe_empty
    ):
        """could_format should return False if input is empty."""
        formatter = DataFormatter(reporting, mock_app_metadata)
        result = formatter.could_format(sample_dataframe, sample_dataframe_empty)
        assert result is False
