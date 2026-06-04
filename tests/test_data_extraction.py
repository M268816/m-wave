# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
"""
Tests for src/data_extraction.py - Excel and CSV data extraction.
"""

import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import MagicMock, patch, call
from src.mtl.extraction import DataExtractor

# ---------------------------------------------------------------------------
# Fixtures (local overrides — conftest.py fixtures are also available)
# ---------------------------------------------------------------------------


@pytest.fixture
def extractor(reporting, mock_app_metadata):
    """A DataExtractor wired to the shared reporting + metadata fixtures."""
    return DataExtractor(reporting, mock_app_metadata)


@pytest.fixture
def sample_excel_df():
    """A small DataFrame that simulates what xlwings would return."""
    return pd.DataFrame(
        {
            "Name": ["Alpha", "Beta", "Gamma"],
            "ID": [1, 2, 3],
            "Type": ["TypeA", "TypeB", "TypeA"],
            "Value": ["10", "20", "30"],
        }
    )


# ---------------------------------------------------------------------------
# TestDataExtractorInit
# ---------------------------------------------------------------------------


class TestDataExtractorInit:
    """Tests for DataExtractor.__init__."""

    def test_init_stores_report(self, reporting, mock_app_metadata):
        """DataExtractor should store the reporting instance as self.report."""
        extractor = DataExtractor(reporting, mock_app_metadata)
        assert extractor.report is reporting

    def test_init_stores_metadata(self, reporting, mock_app_metadata):
        """DataExtractor should store the metadata instance as self.metadata."""
        extractor = DataExtractor(reporting, mock_app_metadata)
        assert extractor.metadata is mock_app_metadata


# ---------------------------------------------------------------------------
# TestExtractMtlTable
# ---------------------------------------------------------------------------


class TestExtractMtlTable:
    """Tests for DataExtractor.extract_mtl_table."""

    @patch("src.data_extraction.xl.App")
    def test_returns_dataframe_on_success(
        self, mock_xl_app, extractor, sample_excel_df
    ):
        """extract_mtl_table should return a DataFrame when xlwings succeeds."""
        mock_app = MagicMock()
        mock_xl_app.return_value = mock_app

        mock_workbook = MagicMock()
        mock_app.books.open.return_value = mock_workbook

        mock_worksheet = MagicMock()
        mock_workbook.sheets.__getitem__.return_value = mock_worksheet

        mock_table = MagicMock()
        mock_worksheet.tables.__getitem__.return_value = mock_table

        mock_table.range.options.return_value.value = sample_excel_df

        result = extractor.extract_mtl_table("fake_mtl.xlsx")

        assert isinstance(result, pd.DataFrame)
        assert not result.empty

    @patch("src.data_extraction.xl.App")
    def test_workbook_is_closed_after_success(
        self, mock_xl_app, extractor, sample_excel_df
    ):
        """extract_mtl_table should close the workbook in the finally block."""
        mock_app = MagicMock()
        mock_xl_app.return_value = mock_app

        mock_workbook = MagicMock()
        mock_app.books.open.return_value = mock_workbook

        mock_worksheet = MagicMock()
        mock_workbook.sheets.__getitem__.return_value = mock_worksheet

        mock_table = MagicMock()
        mock_worksheet.tables.__getitem__.return_value = mock_table
        mock_table.range.options.return_value.value = sample_excel_df

        extractor.extract_mtl_table("fake_mtl.xlsx")

        mock_workbook.close.assert_called_once()

    @patch("src.data_extraction.xl.App")
    def test_excel_is_quit_after_success(self, mock_xl_app, extractor, sample_excel_df):
        """extract_mtl_table should quit the xl.App in the finally block."""
        mock_app = MagicMock()
        mock_xl_app.return_value = mock_app

        mock_workbook = MagicMock()
        mock_app.books.open.return_value = mock_workbook

        mock_worksheet = MagicMock()
        mock_workbook.sheets.__getitem__.return_value = mock_worksheet

        mock_table = MagicMock()
        mock_worksheet.tables.__getitem__.return_value = mock_table
        mock_table.range.options.return_value.value = sample_excel_df

        extractor.extract_mtl_table("fake_mtl.xlsx")

        mock_app.quit.assert_called_once()

    @patch("src.data_extraction.xl.App")
    def test_returns_empty_dataframe_on_exception(self, mock_xl_app, extractor):
        """extract_mtl_table should return an empty DataFrame if xlwings raises."""
        mock_app = MagicMock()
        mock_xl_app.return_value = mock_app
        mock_app.books.open.side_effect = Exception("File not found")

        result = extractor.extract_mtl_table("bad_path.xlsx")

        assert isinstance(result, pd.DataFrame)
        assert result.empty

    @patch("src.data_extraction.xl.App")
    def test_excel_quit_called_even_on_exception(self, mock_xl_app, extractor):
        """extract_mtl_table should still quit xl.App even when an exception occurs."""
        mock_app = MagicMock()
        mock_xl_app.return_value = mock_app
        mock_app.books.open.side_effect = Exception("Crash")

        extractor.extract_mtl_table("bad_path.xlsx")

        mock_app.quit.assert_called_once()

    @patch("src.data_extraction.xl.App")
    def test_uses_metadata_for_worksheet_name(
        self, mock_xl_app, extractor, mock_app_metadata, sample_excel_df
    ):
        """extract_mtl_table should use metadata.get_worksheet_name() for the sheet lookup."""
        mock_app = MagicMock()
        mock_xl_app.return_value = mock_app

        mock_workbook = MagicMock()
        mock_app.books.open.return_value = mock_workbook

        mock_worksheet = MagicMock()
        mock_workbook.sheets.__getitem__.return_value = mock_worksheet

        mock_table = MagicMock()
        mock_worksheet.tables.__getitem__.return_value = mock_table
        mock_table.range.options.return_value.value = sample_excel_df

        extractor.extract_mtl_table("fake_mtl.xlsx")

        mock_workbook.sheets.__getitem__.assert_called_once_with(
            mock_app_metadata.get_worksheet_name.return_value
        )

    @patch("src.data_extraction.xl.App")
    def test_uses_metadata_for_table_id(
        self, mock_xl_app, extractor, mock_app_metadata, sample_excel_df
    ):
        """extract_mtl_table should use metadata.get_table_id() for the table lookup."""
        mock_app = MagicMock()
        mock_xl_app.return_value = mock_app

        mock_workbook = MagicMock()
        mock_app.books.open.return_value = mock_workbook

        mock_worksheet = MagicMock()
        mock_workbook.sheets.__getitem__.return_value = mock_worksheet

        mock_table = MagicMock()
        mock_worksheet.tables.__getitem__.return_value = mock_table
        mock_table.range.options.return_value.value = sample_excel_df

        extractor.extract_mtl_table("fake_mtl.xlsx")

        mock_worksheet.tables.__getitem__.assert_called_once_with(
            mock_app_metadata.get_table_id.return_value
        )


# ---------------------------------------------------------------------------
# TestExtractInputCsv
# ---------------------------------------------------------------------------


class TestExtractInputCsv:
    """Tests for DataExtractor.extract_input_csv."""

    def test_returns_dataframe_from_valid_csv(self, extractor, sample_csv_file):
        """extract_input_csv should return a DataFrame from a valid UTF-8 CSV."""
        result = extractor.extract_input_csv(sample_csv_file, "test")

        assert isinstance(result, pd.DataFrame)
        assert not result.empty
        assert "Name" in result.columns

    def test_csv_row_count_matches_file(self, extractor, sample_csv_file):
        """extract_input_csv should return the correct number of rows."""
        result = extractor.extract_input_csv(sample_csv_file, "test")
        assert len(result) == 2

    def test_csv_columns_match_header(self, extractor, sample_csv_file):
        """extract_input_csv should return columns matching the CSV header."""
        result = extractor.extract_input_csv(sample_csv_file, "test")
        assert list(result.columns) == ["Name", "ID", "Type", "Value"]

    def test_returns_empty_dataframe_on_bad_path(self, extractor):
        """extract_input_csv should return an empty DataFrame for a non-existent file."""
        result = extractor.extract_input_csv("non_existent_file.csv", "test")
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_na_values_are_parsed(self, extractor, tmp_path):
        """extract_input_csv should convert None/null/empty strings to NaN."""
        csv_content = "Name,Value\nItem1,None\nItem2,null\nItem3,\n"
        csv_file = tmp_path / "na_test.csv"
        csv_file.write_text(csv_content, encoding="utf-8")

        result = extractor.extract_input_csv(str(csv_file), "na_test")

        assert result["Value"].isna().all()

    def test_latin1_fallback_on_unicode_error(self, extractor, tmp_path):
        """extract_input_csv should fall back to latin-1 on UnicodeDecodeError."""
        # Write a file with a latin-1 encoded byte (degree symbol)
        csv_content = b"Name,Value\nItem1,30\xb0C\n"
        csv_file = tmp_path / "latin1_test.csv"
        csv_file.write_bytes(csv_content)

        result = extractor.extract_input_csv(str(csv_file), "latin1_test")

        assert isinstance(result, pd.DataFrame)
        assert not result.empty
