"""
Tests for src/data_appender.py - Data append and upsert functionality.
"""

import pytest
import pandas as pd
from src.data_appender import DataAppender


class TestDataAppenderUpsert:
    """Tests for upsert method."""

    def test_upsert_appends_new_rows(self, reporting, mock_app_metadata):
        """upsert should append new rows not in MTL."""
        appender = DataAppender(reporting, mock_app_metadata)

        mtl_df = pd.DataFrame(
            {
                "Name": ["Item1", "Item2"],
                "ID": [1, 2],
                "Value": ["100", "200"],
            }
        )

        input_df = pd.DataFrame(
            {
                "Name": ["Item3", "Item4"],
                "ID": [3, 4],
                "Value": ["300", "400"],
            }
        )

        result = appender.upsert(mtl_df, input_df)

        assert len(result) == 4
        assert "Item3" in result["Name"].values
        assert "Item4" in result["Name"].values

    def test_upsert_updates_existing_rows(self, reporting, mock_app_metadata):
        """upsert should update values for matching keys."""
        appender = DataAppender(reporting, mock_app_metadata)

        mtl_df = pd.DataFrame(
            {
                "Name": ["Item1", "Item2"],
                "ID": [1, 2],
                "Value": ["100", "200"],
            }
        )

        input_df = pd.DataFrame(
            {
                "Name": ["Item1"],
                "ID": [1],
                "Value": ["999"],  # Updated value
            }
        )

        result = appender.upsert(mtl_df, input_df)

        # Should have 2 rows total
        assert len(result) == 2
        # Item1 should have updated value
        item1_row = result[result["Name"] == "Item1"]
        assert item1_row["Value"].iloc[0] == "999"  # type: ignore

    def test_upsert_preserves_mtl_columns(self, reporting, mock_app_metadata):
        """upsert should preserve original column order."""
        appender = DataAppender(reporting, mock_app_metadata)

        original_cols = ["Name", "ID", "Value"]
        mtl_df = pd.DataFrame(
            {
                "Name": ["Item1"],
                "ID": [1],
                "Value": ["100"],
            }
        )

        input_df = pd.DataFrame(
            {
                "Name": ["Item2"],
                "ID": [2],
                "Value": ["200"],
            }
        )

        result = appender.upsert(mtl_df, input_df)

        assert list(result.columns) == original_cols

    def test_upsert_empty_input(self, reporting, mock_app_metadata):
        """upsert with empty input should return MTL data."""
        appender = DataAppender(reporting, mock_app_metadata)

        mtl_df = pd.DataFrame(
            {
                "Name": ["Item1"],
                "ID": [1],
            }
        )

        input_df = pd.DataFrame(
            {
                "Name": [],
                "ID": [],
            }
        )

        result = appender.upsert(mtl_df, input_df)

        assert len(result) == 1

    def test_upsert_empty_mtl(self, reporting, mock_app_metadata):
        """upsert with empty MTL should return input data."""
        appender = DataAppender(reporting, mock_app_metadata)

        mtl_df = pd.DataFrame(
            {
                "Name": [],
                "ID": [],
            }
        )

        input_df = pd.DataFrame(
            {
                "Name": ["Item1"],
                "ID": [1],
            }
        )

        result = appender.upsert(mtl_df, input_df)

        assert len(result) == 1

    def test_upsert_missing_key_returns_empty(self, reporting, mock_app_metadata):
        """upsert with missing index key should return empty df."""
        appender = DataAppender(reporting, mock_app_metadata)

        mtl_df = pd.DataFrame(
            {
                "Name": ["Item1"],
                "Value": ["100"],
                # Missing "ID"
            }
        )

        input_df = pd.DataFrame(
            {
                "Name": ["Item2"],
                "ID": [2],
                "Value": ["200"],
            }
        )

        result = appender.upsert(mtl_df, input_df)

        assert result.empty  # Should fail gracefully


class TestDataAppenderExportToCsv:
    """Tests for export_to_csv method."""

    def test_export_to_csv_creates_file(self, reporting, mock_app_metadata):
        """export_to_csv should create a CSV file."""
        appender = DataAppender(reporting, mock_app_metadata)

        df = pd.DataFrame(
            {
                "Name": ["Item1", "Item2"],
                "Value": ["100", "200"],
            }
        )

        appender.export_to_csv(df)

        expected_file = reporting.report_folder / "mtl_dataframe_after.csv"
        assert expected_file.exists()

    def test_export_to_csv_preserves_data(self, reporting, mock_app_metadata):
        """export_to_csv should preserve all data."""
        appender = DataAppender(reporting, mock_app_metadata)

        df = pd.DataFrame(
            {
                "Name": ["Item1", "Item2"],
                "Value": ["100", "200"],
            }
        )

        appender.export_to_csv(df)

        expected_file = reporting.report_folder / "mtl_dataframe_after.csv"
        saved_df = pd.read_csv(expected_file)

        assert len(saved_df) == 2
        assert list(saved_df.columns) == ["Name", "Value"]
        assert saved_df["Name"].iloc[0] == "Item1"
