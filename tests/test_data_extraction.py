"""
Tests for src/data_extraction.py - Data extraction from Excel and CSV.
"""

import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.data_extraction import DataExtractor


class TestDataExtractorExtractInputCsv:
    """Tests for extract_input_csv method."""

    def test_extract_input_csv_success(
        self, reporting, mock_app_metadata, sample_csv_file
    ):
        """extract_input_csv should read and return CSV as dataframe."""
        extractor = DataExtractor(reporting, mock_app_metadata)

        result = extractor.extract_input_csv(sample_csv_file, "test_filter")

        assert isinstance(result, pd.DataFrame)
        assert not result.empty
        assert "Name" in result.columns
        assert "ID" in result.columns

    def test_extract_input_csv_preserves_data(
        self, reporting, mock_app_metadata, sample_csv_file
    ):
        """extract_input_csv should preserve all data from CSV."""
        extractor = DataExtractor(reporting, mock_app_metadata)

        result = extractor.extract_input_csv(sample_csv_file, "")

        assert len(result) == 2  # Two data rows
        assert result["Name"].iloc[0] == "Item1"
        assert result["ID"].iloc[0] == 1

    def test_extract_input_csv_handles_na_values(
        self, reporting, mock_app_metadata, tmp_path
    ):
        """extract_input_csv should convert na_values to NaN."""
        csv_file = tmp_path / "test_na.csv"
        csv_content = "Name,Value\nItem1,100\nItem2,\nItem3,null\n"
        csv_file.write_text(csv_content, encoding="utf-8")

        extractor = DataExtractor(reporting, mock_app_metadata)
        result = extractor.extract_input_csv(str(csv_file), "")

        # Empty and "null" should be NaN
        assert pd.isna(result["Value"].iloc[1])

    def test_extract_input_csv_encoding_fallback(
        self, reporting, mock_app_metadata, tmp_path
    ):
        """extract_input_csv should fallback to latin-1 on unicode error."""
        csv_file = tmp_path / "test_encoding.csv"
        # This would trigger encoding error in real scenario
        csv_file.write_text("Name,Value\nItem1,100\n", encoding="utf-8")

        extractor = DataExtractor(reporting, mock_app_metadata)
        result = extractor.extract_input_csv(str(csv_file), "test_filter")

        assert not result.empty

    def test_extract_input_csv_missing_file(self, reporting, mock_app_metadata):
        """extract_input_csv should return empty df for missing file."""
        extractor = DataExtractor(reporting, mock_app_metadata)

        result = extractor.extract_input_csv("/nonexistent/file.csv", "")

        assert isinstance(result, pd.DataFrame)
        assert result.empty


class TestDataExtractorCouldExtract:
    """Tests for could_extract method."""

    def test_could_extract_both_valid(
        self, reporting, mock_app_metadata, sample_dataframe
    ):
        """could_extract should return True for valid dataframes."""
        extractor = DataExtractor(reporting, mock_app_metadata)

        result = extractor.could_extract(sample_dataframe, sample_dataframe)

        assert result is True

    def test_could_extract_empty_mtl(
        self, reporting, mock_app_metadata, sample_dataframe_empty, sample_dataframe
    ):
        """could_extract should return False for empty MTL."""
        extractor = DataExtractor(reporting, mock_app_metadata)

        result = extractor.could_extract(sample_dataframe_empty, sample_dataframe)

        assert result is False

    def test_could_extract_empty_input(
        self, reporting, mock_app_metadata, sample_dataframe, sample_dataframe_empty
    ):
        """could_extract should return False for empty input."""
        extractor = DataExtractor(reporting, mock_app_metadata)

        result = extractor.could_extract(sample_dataframe, sample_dataframe_empty)

        assert result is False

    def test_could_extract_both_empty(
        self, reporting, mock_app_metadata, sample_dataframe_empty
    ):
        """could_extract should return False for both empty."""
        extractor = DataExtractor(reporting, mock_app_metadata)

        result = extractor.could_extract(sample_dataframe_empty, sample_dataframe_empty)

        assert result is False

    def test_could_extract_logs_dimensions(
        self, reporting, mock_app_metadata, sample_dataframe
    ):
        """could_extract should log dataframe dimensions."""
        extractor = DataExtractor(reporting, mock_app_metadata)
        initial_lines = len(reporting.report_lines)

        extractor.could_extract(sample_dataframe, sample_dataframe)

        # Should have added info about dimensions
        assert len(reporting.report_lines) > initial_lines
