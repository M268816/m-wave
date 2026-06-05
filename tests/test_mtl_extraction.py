# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved

"""
Tests for src/mtl/extraction.py -- DataExtractor.
xlwings is patched at src.mtl.extraction so no Excel install is needed.
No GUI dependency.
"""

import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from src.mtl.extraction import DataExtractor


SAMPLE_DF = pd.DataFrame(
    {
        "Name": ["Alpha", "Beta", "Gamma"],
        "ID": [1, 2, 3],
        "Type": ["TypeA", "TypeB", "TypeA"],
        "Value": ["10", "20", "30"],
    }
)


# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------

class TestDataExtractorInit:

    def test_stores_report(self, reporting, mock_app_metadata):
        ex = DataExtractor(reporting, mock_app_metadata)
        assert ex.report is reporting

    def test_stores_metadata(self, reporting, mock_app_metadata):
        ex = DataExtractor(reporting, mock_app_metadata)
        assert ex.metadata is mock_app_metadata


# ---------------------------------------------------------------------------
# extract_mtl_table
# ---------------------------------------------------------------------------

class TestExtractMtlTable:

    def _wire_xl(self, mock_xl_app, df=SAMPLE_DF):
        """Set up a fully wired xlwings mock chain."""
        mock_app = MagicMock()
        mock_xl_app.return_value = mock_app
        mock_wb = MagicMock()
        mock_app.books.open.return_value = mock_wb
        mock_ws = MagicMock()
        mock_wb.sheets.__getitem__.return_value = mock_ws
        mock_tbl = MagicMock()
        mock_ws.tables.__getitem__.return_value = mock_tbl
        mock_tbl.range.options.return_value.value = df
        return mock_app, mock_wb

    @patch("src.mtl.extraction.xl.App")
    def test_returns_dataframe_on_success(self, mock_xl, extractor):
        self._wire_xl(mock_xl)
        result = extractor.extract_mtl_table("fake.xlsx")
        assert isinstance(result, pd.DataFrame)
        assert not result.empty

    @patch("src.mtl.extraction.xl.App")
    def test_workbook_closed_after_success(self, mock_xl, extractor):
        _, mock_wb = self._wire_xl(mock_xl)
        extractor.extract_mtl_table("fake.xlsx")
        mock_wb.close.assert_called_once()

    @patch("src.mtl.extraction.xl.App")
    def test_excel_quit_after_success(self, mock_xl, extractor):
        mock_app, _ = self._wire_xl(mock_xl)
        extractor.extract_mtl_table("fake.xlsx")
        mock_app.quit.assert_called_once()

    @patch("src.mtl.extraction.xl.App")
    def test_returns_empty_on_exception(self, mock_xl, extractor):
        mock_app = MagicMock()
        mock_xl.return_value = mock_app
        mock_app.books.open.side_effect = Exception("not found")
        result = extractor.extract_mtl_table("bad.xlsx")
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    @patch("src.mtl.extraction.xl.App")
    def test_excel_quit_called_even_on_exception(self, mock_xl, extractor):
        mock_app = MagicMock()
        mock_xl.return_value = mock_app
        mock_app.books.open.side_effect = Exception("crash")
        extractor.extract_mtl_table("bad.xlsx")
        mock_app.quit.assert_called_once()

    @patch("src.mtl.extraction.xl.App")
    def test_uses_metadata_worksheet_name(self, mock_xl, extractor, mock_app_metadata):
        mock_app, mock_wb = self._wire_xl(mock_xl)
        extractor.extract_mtl_table("fake.xlsx")
        mock_wb.sheets.__getitem__.assert_called_once_with(
            mock_app_metadata.get_worksheet_name.return_value
        )

    @patch("src.mtl.extraction.xl.App")
    def test_uses_metadata_table_id(self, mock_xl, extractor, mock_app_metadata):
        mock_app, mock_wb = self._wire_xl(mock_xl)
        mock_ws = mock_wb.sheets.__getitem__.return_value
        extractor.extract_mtl_table("fake.xlsx")
        mock_ws.tables.__getitem__.assert_called_once_with(
            mock_app_metadata.get_table_id.return_value
        )


# ---------------------------------------------------------------------------
# extract_input_csv
# ---------------------------------------------------------------------------

class TestExtractInputCsv:

    def test_returns_dataframe_from_valid_csv(self, extractor, sample_csv_file):
        result = extractor.extract_input_csv(sample_csv_file, "test")
        assert isinstance(result, pd.DataFrame)
        assert not result.empty
        assert "Name" in result.columns

    def test_row_count_matches_file(self, extractor, sample_csv_file):
        assert len(extractor.extract_input_csv(sample_csv_file, "test")) == 2

    def test_columns_match_header(self, extractor, sample_csv_file):
        assert list(
            extractor.extract_input_csv(sample_csv_file, "test").columns
        ) == ["Name", "ID", "Type", "Value"]

    def test_returns_empty_on_bad_path(self, extractor):
        result = extractor.extract_input_csv("no_such_file.csv", "test")
        assert result.empty

    def test_na_values_parsed(self, extractor, tmp_path):
        f = tmp_path / "na.csv"
        f.write_text("Name,Value\nA,None\nB,null\nC,\n", encoding="utf-8")
        result = extractor.extract_input_csv(str(f), "na")
        assert result["Value"].isna().all()

    def test_latin1_fallback(self, extractor, tmp_path):
        f = tmp_path / "latin1.csv"
        f.write_bytes(b"Name,Value\nItem1,30\xb0C\n")
        result = extractor.extract_input_csv(str(f), "latin1")
        assert isinstance(result, pd.DataFrame)
        assert not result.empty


# ---------------------------------------------------------------------------
# could_extract
# ---------------------------------------------------------------------------

class TestCouldExtract:

    def test_returns_true_when_both_non_empty(self, extractor, sample_dataframe):
        assert extractor.could_extract(sample_dataframe, sample_dataframe) is True

    def test_returns_false_when_mtl_empty(self, extractor, sample_dataframe):
        assert extractor.could_extract(pd.DataFrame(), sample_dataframe) is False

    def test_returns_false_when_input_empty(self, extractor, sample_dataframe):
        assert extractor.could_extract(sample_dataframe, pd.DataFrame()) is False
