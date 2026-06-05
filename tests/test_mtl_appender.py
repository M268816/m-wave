# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved

"""
Tests for src/mtl/appender.py -- DataAppender.
xlwings is patched at src.mtl.appender so no Excel install is needed.
No GUI dependency.
"""

import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from src.mtl.appender import DataAppender


class TestDataAppenderInit:

    def test_stores_report(self, reporting, mock_app_metadata):
        ap = DataAppender(reporting, mock_app_metadata)
        assert ap.report is reporting

    def test_stores_metadata(self, reporting, mock_app_metadata):
        ap = DataAppender(reporting, mock_app_metadata)
        assert ap.metadata is mock_app_metadata


class TestUpsert:

    def test_returns_dataframe(self, appender, mtl_dataframe, input_dataframe):
        assert isinstance(appender.upsert(mtl_dataframe, input_dataframe), pd.DataFrame)

    def test_result_has_correct_row_count(self, appender, mtl_dataframe, input_dataframe):
        # Alpha, Gamma (unchanged MTL) + Beta (updated) + Delta (new) = 4
        assert len(appender.upsert(mtl_dataframe, input_dataframe)) == 4

    def test_matching_row_is_updated(self, appender, mtl_dataframe, input_dataframe):
        result = appender.upsert(mtl_dataframe, input_dataframe)
        beta = result[result["Name"] == "Beta"]
        assert beta["Value"].iloc[0] == "250"

    def test_new_row_is_appended(self, appender, mtl_dataframe, input_dataframe):
        result = appender.upsert(mtl_dataframe, input_dataframe)
        assert "Delta" in result["Name"].values

    def test_unmatched_mtl_rows_preserved(self, appender, mtl_dataframe, input_dataframe):
        result = appender.upsert(mtl_dataframe, input_dataframe)
        assert "Alpha" in result["Name"].values
        assert "Gamma" in result["Name"].values

    def test_column_order_preserved(self, appender, mtl_dataframe, input_dataframe):
        result = appender.upsert(mtl_dataframe, input_dataframe)
        assert result.columns.tolist() == mtl_dataframe.columns.tolist()

    def test_all_new_rows_pure_append(self, appender, mtl_dataframe, input_dataframe_no_matches):
        # 3 MTL + 2 input = 5
        assert len(appender.upsert(mtl_dataframe, input_dataframe_no_matches)) == 5

    def test_returns_empty_on_key_error(self, appender, mtl_dataframe):
        bad = pd.DataFrame({"WrongCol": ["X"]})
        assert appender.upsert(mtl_dataframe, bad).empty

    def test_returns_empty_when_metadata_raises_value_error(self, appender, mtl_dataframe):
        with patch.object(appender, "metadata") as m:
            m.get_table_index_keys.side_effect = ValueError("bad keys")
            assert appender.upsert(mtl_dataframe, mtl_dataframe).empty

    def test_returns_empty_on_none_input(self, appender, mtl_dataframe):
        assert appender.upsert(mtl_dataframe, None).empty

    def test_saves_mtl_before_csv(self, appender, mtl_dataframe, input_dataframe, reporting):
        appender.upsert(mtl_dataframe, input_dataframe)
        assert (reporting.report_folder / "mtl_dataframe_before.csv").exists()

    def test_saves_input_csv(self, appender, mtl_dataframe, input_dataframe, reporting):
        appender.upsert(mtl_dataframe, input_dataframe)
        assert (reporting.report_folder / "input_dataframe.csv").exists()

    def test_calls_get_table_index_keys(self, appender, mtl_dataframe, input_dataframe, mock_app_metadata):
        appender.upsert(mtl_dataframe, input_dataframe)
        mock_app_metadata.get_table_index_keys.assert_called()


class TestExportToCsv:

    def test_creates_file(self, appender, mtl_dataframe, reporting):
        appender.export_to_csv(mtl_dataframe)
        assert (reporting.report_folder / "mtl_dataframe_after.csv").exists()

    def test_file_contains_correct_data(self, appender, mtl_dataframe, reporting):
        appender.export_to_csv(mtl_dataframe)
        saved = pd.read_csv(reporting.report_folder / "mtl_dataframe_after.csv")
        assert len(saved) == len(mtl_dataframe)
        assert list(saved.columns) == list(mtl_dataframe.columns)

    def test_logs_info_messages(self, appender, mtl_dataframe):
        with patch.object(appender, "report") as mock_rpt:
            appender.export_to_csv(mtl_dataframe)
            assert mock_rpt.info.call_count >= 3

    def test_handles_empty_dataframe(self, appender, reporting):
        appender.export_to_csv(pd.DataFrame())
        assert (reporting.report_folder / "mtl_dataframe_after.csv").exists()


class TestExportToMtl:

    def _wire_xl(self, mock_xl_app):
        mock_app = MagicMock()
        mock_xl_app.return_value = mock_app
        mock_wb = MagicMock()
        mock_app.books.open.return_value = mock_wb
        mock_ws = MagicMock()
        mock_wb.sheets.__getitem__.return_value = mock_ws
        mock_tbl = MagicMock()
        mock_ws.tables.__getitem__.return_value = mock_tbl
        return mock_app, mock_wb

    @patch("src.mtl.appender.xl.App")
    def test_opens_excel(self, mock_xl, appender, mtl_dataframe, tmp_path):
        self._wire_xl(mock_xl)
        f = tmp_path / "test.xlsx"
        f.write_text("fake")
        appender.export_to_mtl(mtl_dataframe, str(f))
        mock_xl.assert_called_once_with(visible=False, add_book=False)

    @patch("src.mtl.appender.xl.App")
    def test_opens_mtl_file(self, mock_xl, appender, mtl_dataframe, tmp_path):
        mock_app, _ = self._wire_xl(mock_xl)
        f = tmp_path / "test.xlsx"
        f.write_text("fake")
        appender.export_to_mtl(mtl_dataframe, str(f))
        mock_app.books.open.assert_called()

    @patch("src.mtl.appender.xl.App")
    def test_excel_quit_in_finally(self, mock_xl, appender, mtl_dataframe, tmp_path):
        mock_app, _ = self._wire_xl(mock_xl)
        f = tmp_path / "test.xlsx"
        f.write_text("fake")
        appender.export_to_mtl(mtl_dataframe, str(f))
        mock_app.quit.assert_called_once()
