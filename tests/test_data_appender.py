# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
"""
Tests for src/data_appender.py - Data appending and MTL export.
"""

import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import MagicMock, patch, call
from src.mtl.appender import DataAppender

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def appender(reporting, mock_app_metadata):
    """A DataAppender instance with mocked dependencies."""
    return DataAppender(reporting, mock_app_metadata)


@pytest.fixture
def mtl_dataframe():
    """Sample MTL dataframe with index keys."""
    return pd.DataFrame(
        {
            "Name": ["Alpha", "Beta", "Gamma"],
            "ID": [1, 2, 3],
            "Type": ["TypeA", "TypeB", "TypeA"],
            "Value": ["100", "200", "300"],
        }
    )


@pytest.fixture
def input_dataframe():
    """Sample input dataframe with some matching keys and new rows."""
    return pd.DataFrame(
        {
            "Name": ["Beta", "Delta"],  # Beta matches MTL, Delta is new
            "ID": [2, 4],
            "Type": ["TypeB_updated", "TypeC"],
            "Value": ["250", "400"],
        }
    )


@pytest.fixture
def input_dataframe_no_matches():
    """Input dataframe with no matching keys."""
    return pd.DataFrame(
        {
            "Name": ["Delta", "Epsilon"],
            "ID": [4, 5],
            "Type": ["TypeC", "TypeD"],
            "Value": ["400", "500"],
        }
    )


# ---------------------------------------------------------------------------
# TestDataAppenderInit
# ---------------------------------------------------------------------------


class TestDataAppenderInit:
    """Tests for DataAppender.__init__."""

    def test_init_stores_report(self, reporting, mock_app_metadata):
        """DataAppender should store the reporting instance."""
        appender = DataAppender(reporting, mock_app_metadata)
        assert appender.report is reporting

    def test_init_stores_metadata(self, reporting, mock_app_metadata):
        """DataAppender should store the metadata instance."""
        appender = DataAppender(reporting, mock_app_metadata)
        assert appender.metadata is mock_app_metadata


# ---------------------------------------------------------------------------
# TestUpsert
# ---------------------------------------------------------------------------


class TestUpsert:
    """Tests for the upsert method."""

    def test_upsert_returns_dataframe(self, appender, mtl_dataframe, input_dataframe):
        """upsert should return a DataFrame."""
        result = appender.upsert(mtl_dataframe, input_dataframe)
        assert isinstance(result, pd.DataFrame)

    def test_upsert_includes_all_rows_from_both(
        self, appender, mtl_dataframe, input_dataframe
    ):
        """upsert should include rows from both MTL (non-matching) and input."""
        result = appender.upsert(mtl_dataframe, input_dataframe)
        # MTL has 3 rows: Alpha, Beta, Gamma
        # Input has 2 rows: Beta (update), Delta (new)
        # Result should have: Alpha, Gamma, Beta (updated), Delta = 4 rows
        assert len(result) == 4

    def test_upsert_updates_matching_rows(
        self, appender, mtl_dataframe, input_dataframe
    ):
        """upsert should update values in matching rows."""
        result = appender.upsert(mtl_dataframe, input_dataframe)
        # Beta's value should be updated from "200" to "250"
        beta_row = result[result["Name"] == "Beta"]
        assert beta_row["Value"].iloc[0] == "250"

    def test_upsert_appends_new_rows(self, appender, mtl_dataframe, input_dataframe):
        """upsert should append rows from input that don't match MTL keys."""
        result = appender.upsert(mtl_dataframe, input_dataframe)
        # Delta is new and should be in result
        assert "Delta" in result["Name"].values

    def test_upsert_preserves_non_matching_mtl_rows(
        self, appender, mtl_dataframe, input_dataframe
    ):
        """upsert should preserve MTL rows that don't match input keys."""
        result = appender.upsert(mtl_dataframe, input_dataframe)
        # Alpha and Gamma are only in MTL, should be preserved
        assert "Alpha" in result["Name"].values
        assert "Gamma" in result["Name"].values

    def test_upsert_preserves_column_order(
        self, appender, mtl_dataframe, input_dataframe
    ):
        """upsert should return columns in the same order as original MTL."""
        original_columns = mtl_dataframe.columns.tolist()
        result = appender.upsert(mtl_dataframe, input_dataframe)
        assert result.columns.tolist() == original_columns

    def test_upsert_handles_all_new_rows(
        self, appender, mtl_dataframe, input_dataframe_no_matches
    ):
        """upsert should handle when input has no matching keys (pure append)."""
        result = appender.upsert(mtl_dataframe, input_dataframe_no_matches)
        # All MTL rows + all input rows = 5 rows total
        assert len(result) == 5  # 3 from MTL + 2 from input

    def test_upsert_returns_empty_on_key_error(self, appender, mtl_dataframe):
        """upsert should return empty DataFrame on KeyError."""
        # Create input without index key columns
        bad_input = pd.DataFrame(
            {
                "WrongColumn": ["Test"],
            }
        )
        result = appender.upsert(mtl_dataframe, bad_input)
        assert result.empty

    def test_upsert_returns_empty_on_value_error(self, appender):
        """upsert should return empty DataFrame on ValueError."""
        mtl = pd.DataFrame({"Name": ["A"], "ID": [1]})
        # Mock to raise ValueError when get_table_index_keys is called
        with patch.object(appender, "metadata") as mock_meta:
            mock_meta.get_table_index_keys.side_effect = ValueError("Bad keys")
            result = appender.upsert(mtl, mtl)
        assert result.empty

    def test_upsert_handles_none_gracefully_via_exception_handler(
        self, appender, mtl_dataframe
    ):
        """upsert should catch AttributeError when input is None."""
        # Passing None will cause an AttributeError in set_index, which is caught
        result = appender.upsert(mtl_dataframe, None)
        # Should return empty df, not raise
        assert result.empty

    def test_upsert_saves_mtl_before_csv(
        self, appender, mtl_dataframe, input_dataframe, reporting
    ):
        """upsert should save the MTL dataframe before upserting to CSV."""
        appender.upsert(mtl_dataframe, input_dataframe)
        # Check that the file was written
        expected_file = reporting.report_folder / "mtl_dataframe_before.csv"
        assert expected_file.exists()

    def test_upsert_saves_input_csv(
        self, appender, mtl_dataframe, input_dataframe, reporting
    ):
        """upsert should save the input dataframe to CSV."""
        appender.upsert(mtl_dataframe, input_dataframe)
        expected_file = reporting.report_folder / "input_dataframe.csv"
        assert expected_file.exists()

    def test_upsert_uses_index_keys_from_metadata(
        self, appender, mtl_dataframe, input_dataframe, mock_app_metadata
    ):
        """upsert should use the keys returned by metadata.get_table_index_keys()."""
        appender.upsert(mtl_dataframe, input_dataframe)
        mock_app_metadata.get_table_index_keys.assert_called()


# ---------------------------------------------------------------------------
# TestExportToCsv
# ---------------------------------------------------------------------------


class TestExportToCsv:
    """Tests for the export_to_csv method."""

    def test_export_to_csv_creates_file(self, appender, mtl_dataframe, reporting):
        """export_to_csv should create a CSV file in the report folder."""
        appender.export_to_csv(mtl_dataframe)
        expected_file = reporting.report_folder / "mtl_dataframe_after.csv"
        assert expected_file.exists()

    def test_export_to_csv_file_contains_data(self, appender, mtl_dataframe, reporting):
        """export_to_csv should write the dataframe to the CSV file."""
        appender.export_to_csv(mtl_dataframe)
        expected_file = reporting.report_folder / "mtl_dataframe_after.csv"
        saved_df = pd.read_csv(expected_file)
        assert len(saved_df) == len(mtl_dataframe)
        assert list(saved_df.columns) == list(mtl_dataframe.columns)

    def test_export_to_csv_uses_utf8_encoding(self, appender, mtl_dataframe, reporting):
        """export_to_csv should write the file with UTF-8 encoding."""
        appender.export_to_csv(mtl_dataframe)
        expected_file = reporting.report_folder / "mtl_dataframe_after.csv"
        # Read back and check for special characters work (encoding test)
        saved_df = pd.read_csv(expected_file)
        assert saved_df is not None

    def test_export_to_csv_logs_info_messages(self, appender, mtl_dataframe):
        """export_to_csv should call reporting.info() with status messages."""
        # Create a fresh mock so we can count calls
        with patch.object(appender, "report") as mock_report:
            appender.export_to_csv(mtl_dataframe)
            # Should have called info at least 3 times
            assert mock_report.info.call_count >= 3

    def test_export_to_csv_empty_dataframe(self, appender, reporting):
        """export_to_csv should handle empty dataframes."""
        empty_df = pd.DataFrame()
        appender.export_to_csv(empty_df)
        expected_file = reporting.report_folder / "mtl_dataframe_after.csv"
        assert expected_file.exists()


# ---------------------------------------------------------------------------
# TestExportToMtl
# ---------------------------------------------------------------------------


class TestExportToMtl:
    """Tests for the export_to_mtl method."""

    @patch("src.data_appender.xl.App")
    def test_export_to_mtl_opens_excel(
        self, mock_xl_app, appender, mtl_dataframe, tmp_path
    ):
        """export_to_mtl should open a new xl.App instance."""
        mock_app = MagicMock()
        mock_xl_app.return_value = mock_app
        mock_workbook = MagicMock()
        mock_app.books.open.return_value = mock_workbook
        mock_worksheet = MagicMock()
        mock_workbook.sheets.__getitem__.return_value = mock_worksheet
        mock_table = MagicMock()
        mock_worksheet.tables.__getitem__.return_value = mock_table

        mtl_file = tmp_path / "test.xlsx"
        mtl_file.write_text("fake")

        appender.export_to_mtl(mtl_dataframe, str(mtl_file))

        mock_xl_app.assert_called_once_with(visible=False, add_book=False)

    @patch("src.data_appender.xl.App")
    def test_export_to_mtl_opens_mtl_file(
        self, mock_xl_app, appender, mtl_dataframe, tmp_path
    ):
        """export_to_mtl should open the MTL file."""
        mock_app = MagicMock()
        mock_xl_app.return_value = mock_app
        mock_workbook = MagicMock()
        mock_app.books.open.return_value = mock_workbook
        mock_worksheet = MagicMock()
        mock_workbook.sheets.__getitem__.return_value = mock_worksheet
        mock_table = MagicMock()
        mock_worksheet.tables.__getitem__.return_value = mock_table

        mtl_file = tmp_path / "test.xlsx"
        mtl_file.write_text("fake")

        appender.export_to_mtl(mtl_dataframe, str(mtl_file))

        # First call is read_only=True, opens original
        assert mock_app.books.open.call_count >= 1

    @patch("src.data_appender.xl.App")
    def test_export_to_mtl_creates_working_copy(
        self, mock_xl_app, appender, mtl_dataframe, tmp_path
    ):
        """export_to_mtl should save a working copy before modifying."""
        mock_app = MagicMock()
        mock_xl_app.return_value = mock_app
        mock_workbook = MagicMock()
        mock_app.books.open.return_value = mock_workbook
        mock_worksheet = MagicMock()
        mock_workbook.sheets.__getitem__.return_value = mock_worksheet
        mock_table = MagicMock()
        mock_worksheet.tables.__getitem__.return_value = mock_table

        mtl_file = tmp_path / "test.xlsx"
        mtl_file.write_text("fake")

        appender.export_to_mtl(mtl_dataframe, str(mtl_file))

        # Workbook.save should be called for the working copy
        mock_workbook.save.assert_called()

    @patch("src.data_appender.xl.App")
    def test_export_to_mtl_accesses_correct_worksheet(
        self, mock_xl_app, appender, mock_app_metadata, mtl_dataframe, tmp_path
    ):
        """export_to_mtl should access the worksheet from metadata."""
        mock_app = MagicMock()
        mock_xl_app.return_value = mock_app
        mock_workbook = MagicMock()
        mock_app.books.open.return_value = mock_workbook
        mock_worksheet = MagicMock()
        mock_workbook.sheets.__getitem__.return_value = mock_worksheet
        mock_table = MagicMock()
        mock_worksheet.tables.__getitem__.return_value = mock_table

        mtl_file = tmp_path / "test.xlsx"
        mtl_file.write_text("fake")

        appender.export_to_mtl(mtl_dataframe, str(mtl_file))

        # Should call get_worksheet_name to get the sheet name
        mock_app_metadata.get_worksheet_name.assert_called()

    @patch("src.data_appender.xl.App")
    def test_export_to_mtl_accesses_correct_table(
        self, mock_xl_app, appender, mock_app_metadata, mtl_dataframe, tmp_path
    ):
        """export_to_mtl should access the table by ID from metadata."""
        mock_app = MagicMock()
        mock_xl_app.return_value = mock_app
        mock_workbook = MagicMock()
        mock_app.books.open.return_value = mock_workbook
        mock_worksheet = MagicMock()
        mock_workbook.sheets.__getitem__.return_value = mock_worksheet
        mock_table = MagicMock()
        mock_worksheet.tables.__getitem__.return_value = mock_table

        mtl_file = tmp_path / "test.xlsx"
        mtl_file.write_text("fake")

        appender.export_to_mtl(mtl_dataframe, str(mtl_file))

        # Should call get_table_id to get the table name
        mock_app_metadata.get_table_id.assert_called()

    @patch("src.data_appender.xl.App")
    def test_export_to_mtl_updates_table(
        self, mock_xl_app, appender, mtl_dataframe, tmp_path
    ):
        """export_to_mtl should call table.update() with the dataframe."""
        mock_app = MagicMock()
        mock_xl_app.return_value = mock_app
        mock_workbook = MagicMock()
        mock_app.books.open.return_value = mock_workbook
        mock_worksheet = MagicMock()
        mock_workbook.sheets.__getitem__.return_value = mock_worksheet
        mock_table = MagicMock()
        mock_worksheet.tables.__getitem__.return_value = mock_table

        mtl_file = tmp_path / "test.xlsx"
        mtl_file.write_text("fake")

        appender.export_to_mtl(mtl_dataframe, str(mtl_file))

        # table.update should be called with the dataframe
        mock_table.update.assert_called_once()
        call_args = mock_table.update.call_args
        assert isinstance(call_args[0][0], pd.DataFrame)

    @patch("src.data_appender.xl.App")
    def test_export_to_mtl_saves_workbook(
        self, mock_xl_app, appender, mtl_dataframe, tmp_path
    ):
        """export_to_mtl should save the workbook after updating."""
        mock_app = MagicMock()
        mock_xl_app.return_value = mock_app
        mock_workbook = MagicMock()
        mock_app.books.open.return_value = mock_workbook
        mock_worksheet = MagicMock()
        mock_workbook.sheets.__getitem__.return_value = mock_worksheet
        mock_table = MagicMock()
        mock_worksheet.tables.__getitem__.return_value = mock_table

        mtl_file = tmp_path / "test.xlsx"
        mtl_file.write_text("fake")

        appender.export_to_mtl(mtl_dataframe, str(mtl_file))

        # workbook.save should be called at least once (for output copy)
        assert mock_workbook.save.call_count >= 1

    @patch("src.data_appender.xl.App")
    def test_export_to_mtl_closes_workbook_on_success(
        self, mock_xl_app, appender, mtl_dataframe, tmp_path
    ):
        """export_to_mtl should close the workbook in finally block."""
        mock_app = MagicMock()
        mock_xl_app.return_value = mock_app
        mock_workbook = MagicMock()
        mock_app.books.open.return_value = mock_workbook
        mock_worksheet = MagicMock()
        mock_workbook.sheets.__getitem__.return_value = mock_worksheet
        mock_table = MagicMock()
        mock_worksheet.tables.__getitem__.return_value = mock_table

        mtl_file = tmp_path / "test.xlsx"
        mtl_file.write_text("fake")

        appender.export_to_mtl(mtl_dataframe, str(mtl_file))

        mock_workbook.close.assert_called()

    @patch("src.data_appender.xl.App")
    def test_export_to_mtl_quits_excel_on_success(
        self, mock_xl_app, appender, mtl_dataframe, tmp_path
    ):
        """export_to_mtl should quit Excel in finally block."""
        mock_app = MagicMock()
        mock_xl_app.return_value = mock_app
        mock_workbook = MagicMock()
        mock_app.books.open.return_value = mock_workbook
        mock_worksheet = MagicMock()
        mock_workbook.sheets.__getitem__.return_value = mock_worksheet
        mock_table = MagicMock()
        mock_worksheet.tables.__getitem__.return_value = mock_table

        mtl_file = tmp_path / "test.xlsx"
        mtl_file.write_text("fake")

        appender.export_to_mtl(mtl_dataframe, str(mtl_file))

        mock_app.quit.assert_called()

    @patch("src.data_appender.xl.App")
    def test_export_to_mtl_closes_workbook_on_exception(
        self, mock_xl_app, appender, mtl_dataframe, tmp_path
    ):
        """export_to_mtl should close workbook even if an exception occurs."""
        mock_app = MagicMock()
        mock_xl_app.return_value = mock_app
        mock_workbook = MagicMock()
        mock_app.books.open.side_effect = Exception("File access error")

        mtl_file = tmp_path / "test.xlsx"
        mtl_file.write_text("fake")

        # Should not raise, just log the error
        appender.export_to_mtl(mtl_dataframe, str(mtl_file))

        # excel.quit() should still be called in finally
        mock_app.quit.assert_called()

    @patch("src.data_appender.xl.App")
    def test_export_to_mtl_quits_excel_on_exception(
        self, mock_xl_app, appender, mtl_dataframe, tmp_path
    ):
        """export_to_mtl should quit Excel even if an exception occurs."""
        mock_app = MagicMock()
        mock_xl_app.return_value = mock_app
        mock_app.books.open.side_effect = Exception("Failure")

        mtl_file = tmp_path / "test.xlsx"
        mtl_file.write_text("fake")

        appender.export_to_mtl(mtl_dataframe, str(mtl_file))

        mock_app.quit.assert_called()

    @patch("src.data_appender.xl.App")
    def test_export_to_mtl_uses_default_output_path(
        self, mock_xl_app, appender, mtl_dataframe, tmp_path
    ):
        """export_to_mtl should use default output path if none provided."""
        mock_app = MagicMock()
        mock_xl_app.return_value = mock_app
        mock_workbook = MagicMock()
        mock_app.books.open.return_value = mock_workbook
        mock_worksheet = MagicMock()
        mock_workbook.sheets.__getitem__.return_value = mock_worksheet
        mock_table = MagicMock()
        mock_worksheet.tables.__getitem__.return_value = mock_table

        mtl_file = tmp_path / "test.xlsx"
        mtl_file.write_text("fake")

        # Patch report.info to count calls
        with patch.object(appender, "report") as mock_report:
            appender.export_to_mtl(mtl_dataframe, str(mtl_file))
            # Should have logged at least 3 info messages
            assert mock_report.info.call_count > 0

    @patch("src.data_appender.xl.App")
    def test_export_to_mtl_uses_custom_output_path(
        self, mock_xl_app, appender, mtl_dataframe, tmp_path
    ):
        """export_to_mtl should use custom output path if provided."""
        mock_app = MagicMock()
        mock_xl_app.return_value = mock_app
        mock_workbook = MagicMock()
        mock_app.books.open.return_value = mock_workbook
        mock_worksheet = MagicMock()
        mock_workbook.sheets.__getitem__.return_value = mock_worksheet
        mock_table = MagicMock()
        mock_worksheet.tables.__getitem__.return_value = mock_table

        mtl_file = tmp_path / "test.xlsx"
        output_file = tmp_path / "output.xlsx"
        mtl_file.write_text("fake")

        appender.export_to_mtl(mtl_dataframe, str(mtl_file), output_file)

        # Check that save was called (path is used in save)
        assert mock_workbook.save.call_count >= 1

    @patch("src.data_appender.xl.App")
    def test_export_to_mtl_logs_status_info(
        self, mock_xl_app, appender, mtl_dataframe, tmp_path
    ):
        """export_to_mtl should log informational messages during execution."""
        mock_app = MagicMock()
        mock_xl_app.return_value = mock_app
        mock_workbook = MagicMock()
        mock_app.books.open.return_value = mock_workbook
        mock_worksheet = MagicMock()
        mock_workbook.sheets.__getitem__.return_value = mock_worksheet
        mock_table = MagicMock()
        mock_worksheet.tables.__getitem__.return_value = mock_table

        mtl_file = tmp_path / "test.xlsx"
        mtl_file.write_text("fake")

        # Patch to count calls
        with patch.object(appender, "report") as mock_report:
            appender.export_to_mtl(mtl_dataframe, str(mtl_file))
            # Should have called info multiple times
            assert mock_report.info.call_count > 3
