"""
Shared pytest fixtures for all test modules.
"""

import pytest
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from unittest.mock import MagicMock, patch
from tempfile import TemporaryDirectory

# Import your classes
from src.reporting import Reporting
from src.metadata import AppMetadata, TableType
from src.mtl.extraction import DataExtractor
from src.mtl.formatter import DataFormatter
from src.mtl.comparator import DataComparator
from src.mtl.appender import DataAppender


@pytest.fixture
def mock_window():
    """A mock Tkinter window for testing."""
    window = MagicMock()
    window.after = MagicMock(side_effect=lambda delay, func: func())
    return window


@pytest.fixture
def temp_report_dir():
    """A temporary directory for report output."""
    with TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def reporting(mock_window, temp_report_dir):
    """A Reporting instance with a mock window and temp directory."""
    report = Reporting(
        parent_window=mock_window,
        output_dir=temp_report_dir,
        verbose_printing=False,
        populate_report=True,
        populate_log=False,
        use_timestamps=True,
        use_msg_types=True,
    )
    report.create_report("test_report")
    report._queue_modal = MagicMock()
    return report


@pytest.fixture
def mock_app_metadata():
    """A mock AppMetadata instance."""
    metadata = MagicMock(spec=AppMetadata)
    metadata.get_worksheet_name.return_value = "TestTable"
    metadata.get_table_id.return_value = "TestTableId"
    metadata.get_table_type.return_value = TableType.ELEMENT
    metadata.get_table_index_keys.return_value = ["Name", "ID"]
    metadata.get_table_filter_keys.return_value = ["Name", "Type"]
    metadata.get_table_sort_order.return_value = ["Name"]
    metadata.get_table_sort_direction.return_value = [True]
    metadata.should_filter_on_keys.return_value = False
    metadata.can_compare_worksheet.return_value = True
    metadata.get_table_formatting.return_value = {
        "Object Type Order": None,
        "Sort Order": ["Name"],
        "Sort Direction": [True],
    }
    return metadata


@pytest.fixture
def sample_dataframe():
    """A sample pandas DataFrame for testing."""
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
    """An empty pandas DataFrame."""
    return pd.DataFrame()


@pytest.fixture
def sample_csv_file(tmp_path):
    """Create a temporary CSV file and return its path."""
    csv_content = "Name,ID,Type,Value\nItem1,1,TypeA,100\nItem2,2,TypeB,200\n"
    csv_file = tmp_path / "test_input.csv"
    csv_file.write_text(csv_content, encoding="utf-8")
    return str(csv_file)
