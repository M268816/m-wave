# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
#
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH

"""
conftest.py -- Shared pytest fixtures for the non-GUI test suite.

All GUI, controller and tkinter/ttkbootstrap dependencies are replaced with a
lightweight MagicMock-based reporting stub so no display or GUI packages are
needed to run the suite.

Fixture index
-------------
Reporting
    reporting           Fully mocked Reporting double; records messages in
                        reporting.report_lines and exposes report_folder.

Metadata
    mock_app_metadata   AppMetadata mock (ELEMENT type, two-key composite index)
    mock_metadata       AppMetadata mock (ANALYTICS type, used by process tests)

DataFrames
    sample_dataframe            Generic 4-column, 3-row DataFrame
    sample_dataframe_empty      Empty DataFrame
    mtl_dataframe               Alpha / Beta / Gamma rows
    input_dataframe             One matching row (Beta) + one new row (Delta)
    input_dataframe_no_matches  No MTL-matching rows

Files
    sample_csv_file     Temp UTF-8 CSV path (string)

Collaborators
    extractor           DataExtractor(reporting, mock_app_metadata)
    appender            DataAppender(reporting, mock_app_metadata)

Process
    process             Process with all four collaborators mocked
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pandas as pd
import pytest


# ===========================================================================
# Reporting stub factory
# ===========================================================================

def _make_reporting_mock(tmp_path: Path) -> MagicMock:
    """
    Return a MagicMock that behaves like Reporting well enough for data /
    process tests.  All log methods append the message string to
    mock.report_lines so tests can assert on content.
    """
    rpt = MagicMock()
    rpt.report_lines = []
    rpt.report_folder = tmp_path
    rpt.cleaned_name = "test_report"
    rpt.file_path = tmp_path / "test_report.log"

    def _record(msg="", *args, **kwargs):
        rpt.report_lines.append(str(msg))

    def _save(*args, **kwargs):
        rpt.file_path.write_text("\n".join(rpt.report_lines), encoding="utf-8")

    for method in (
        "info", "warning", "error", "exception", "debug", "critical",
        "title", "subtitle", "simple_title",
        "highlight_error", "highlight_titled_error",
        "error_separator", "error_section", "error_divider",
        "divider", "separator", "section",
    ):
        getattr(rpt, method).side_effect = _record

    rpt.save_report.side_effect = _save
    return rpt


# ===========================================================================
# Fixtures
# ===========================================================================

# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

@pytest.fixture
def reporting(tmp_path):
    """Mocked Reporting double -- no tkinter or ttkbootstrap required."""
    return _make_reporting_mock(tmp_path)


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_app_metadata():
    """AppMetadata mock with a two-column composite index (Name + ID)."""
    meta = MagicMock()
    meta.get_table_index_keys.return_value = ["Name", "ID"]
    meta.get_table_filter_keys.return_value = ["Name", "Type"]
    meta.get_table_id.return_value = "Table1"
    meta.get_worksheet_name.return_value = "Sheet1"
    meta.get_table_formatting.return_value = {
        "Index Keys": ["Name", "ID"],
        "Filter on Keys": False,
        "Filter Keys": ["Name", "Type"],
        "Object Type Order": None,
        "Sort Order": ["Name"],
        "Sort Direction": [True],
    }
    meta.should_filter_on_keys.return_value = False
    meta.can_compare_worksheet.return_value = True
    return meta


@pytest.fixture
def mock_metadata():
    """AppMetadata mock for ANALYTICS type -- used by process tests."""
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


# ---------------------------------------------------------------------------
# DataFrames
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_dataframe():
    """Generic 3-row DataFrame used across formatter / comparator tests."""
    return pd.DataFrame(
        {
            "Name": ["Item1", "Item2", "Item3"],
            "ID": [1, 2, 3],
            "Type": ["TypeA", "TypeB", "TypeA"],
            "Value": ["100", "200", "150"],
        }
    )


@pytest.fixture
def sample_dataframe_empty():
    """Empty DataFrame sentinel."""
    return pd.DataFrame()


@pytest.fixture
def mtl_dataframe():
    """Sample MTL DataFrame with three rows."""
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
    """Input with Beta (update) and Delta (new row)."""
    return pd.DataFrame(
        {
            "Name": ["Beta", "Delta"],
            "ID": [2, 4],
            "Type": ["TypeB_updated", "TypeC"],
            "Value": ["250", "400"],
        }
    )


@pytest.fixture
def input_dataframe_no_matches():
    """Input DataFrame with no keys matching the MTL."""
    return pd.DataFrame(
        {
            "Name": ["Delta", "Epsilon"],
            "ID": [4, 5],
            "Type": ["TypeC", "TypeD"],
            "Value": ["400", "500"],
        }
    )


# ---------------------------------------------------------------------------
# Files
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_csv_file(tmp_path):
    """A small UTF-8 CSV file; returns path as string."""
    csv_file = tmp_path / "sample.csv"
    csv_file.write_text(
        "Name,ID,Type,Value\nItem1,1,TypeA,100\nItem2,2,TypeB,200\n",
        encoding="utf-8",
    )
    return str(csv_file)


# ---------------------------------------------------------------------------
# Collaborators
# ---------------------------------------------------------------------------

@pytest.fixture
def extractor(reporting, mock_app_metadata):
    """DataExtractor wired to the shared stubs."""
    from src.mtl.extraction import DataExtractor
    return DataExtractor(reporting, mock_app_metadata)


@pytest.fixture
def appender(reporting, mock_app_metadata):
    """DataAppender wired to the shared stubs."""
    from src.mtl.appender import DataAppender
    return DataAppender(reporting, mock_app_metadata)


# ---------------------------------------------------------------------------
# Process
# ---------------------------------------------------------------------------

@pytest.fixture
def process(reporting, mock_metadata):
    """
    Process instance with AppMetadata patched and all four collaborators
    replaced with fresh MagicMocks after construction.
    """
    from src.mtl.process import Process

    with patch("src.mtl.process.AppMetadata", return_value=mock_metadata):
        proc = Process(
            report=reporting,
            filter_string="",
            selected_data_table="TestTable",
            mtl_file_path="/fake/mtl.xlsx",
            input_file_path="/fake/input.csv",
        )

    proc.data_extractor = MagicMock()
    proc.data_formatter = MagicMock()
    proc.data_comparator = MagicMock()
    proc.data_appender = MagicMock()
    return proc


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@pytest.fixture
def valid_config():
    return {"use_timestamps": False, "use_msg_types": False}


@pytest.fixture
def config_json(valid_config):
    return json.dumps(valid_config)


@pytest.fixture
def mock_config_file(config_json):
    return mock_open(read_data=config_json)
