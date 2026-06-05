# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved

"""
Tests for src/mtl/comparator.py -- DataComparator.
No GUI dependency.
"""

import pytest
import pandas as pd
from src.mtl.comparator import DataComparator


class TestCompareShapes:

    def test_equal_shapes(self, reporting, mock_app_metadata):
        cmp = DataComparator(reporting, mock_app_metadata)
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
        result = cmp.compare_shapes(df, df.copy())
        assert result["shapes_equal"] is True
        assert result["row_difference"] == 0
        assert result["column_difference"] == 0

    def test_different_row_count(self, reporting, mock_app_metadata):
        cmp = DataComparator(reporting, mock_app_metadata)
        df1 = pd.DataFrame({"A": [1, 2, 3]})
        df2 = pd.DataFrame({"A": [1, 2]})
        result = cmp.compare_shapes(df1, df2)
        assert result["shapes_equal"] is False
        assert result["row_difference"] == 1

    def test_different_column_count(self, reporting, mock_app_metadata):
        cmp = DataComparator(reporting, mock_app_metadata)
        df1 = pd.DataFrame({"A": [1], "B": [2], "C": [3]})
        df2 = pd.DataFrame({"A": [1], "B": [2]})
        result = cmp.compare_shapes(df1, df2)
        assert result["shapes_equal"] is False
        assert result["column_difference"] == 1

    def test_empty_returns_empty_dict(self, reporting, mock_app_metadata):
        cmp = DataComparator(reporting, mock_app_metadata)
        assert cmp.compare_shapes(pd.DataFrame(), pd.DataFrame()) == {}


class TestCompareRows:

    def _df(self, vals):
        return pd.DataFrame({"Name": ["A", "B"], "ID": [1, 2], "Value": vals})

    def test_identical_data_returns_true(self, reporting, mock_app_metadata):
        cmp = DataComparator(reporting, mock_app_metadata)
        df = self._df(["100", "200"])
        assert cmp.compare_rows(df, df.copy()) is True

    def test_different_values_still_returns_true(self, reporting, mock_app_metadata):
        # compare_rows reports differences but still returns True (not a hard stop)
        cmp = DataComparator(reporting, mock_app_metadata)
        df1 = self._df(["100", "200"])
        df2 = self._df(["100", "999"])
        assert cmp.compare_rows(df1, df2) is True

    def test_empty_mtl_returns_false(self, reporting, mock_app_metadata, sample_dataframe):
        cmp = DataComparator(reporting, mock_app_metadata)
        assert cmp.compare_rows(pd.DataFrame(), sample_dataframe) is False

    def test_empty_input_returns_false(self, reporting, mock_app_metadata, sample_dataframe):
        cmp = DataComparator(reporting, mock_app_metadata)
        assert cmp.compare_rows(sample_dataframe, pd.DataFrame()) is False

    def test_different_row_counts_still_returns_true(self, reporting, mock_app_metadata):
        cmp = DataComparator(reporting, mock_app_metadata)
        df1 = pd.DataFrame({"Name": ["A", "B", "C"], "ID": [1, 2, 3]})
        df2 = pd.DataFrame({"Name": ["A", "B"], "ID": [1, 2]})
        assert cmp.compare_rows(df1, df2) is True


class TestReportShapeDifferences:

    def test_equal_dimensions_reported(self, reporting, mock_app_metadata):
        cmp = DataComparator(reporting, mock_app_metadata)
        cmp._report_shape_differences(5, 5, "ROW")
        assert any("match" in line.lower() for line in reporting.report_lines)

    def test_mtl_larger_reported(self, reporting, mock_app_metadata):
        cmp = DataComparator(reporting, mock_app_metadata)
        cmp._report_shape_differences(10, 5, "ROW")
        assert any("MTL" in line and "5" in line for line in reporting.report_lines)

    def test_input_larger_reported(self, reporting, mock_app_metadata):
        cmp = DataComparator(reporting, mock_app_metadata)
        cmp._report_shape_differences(3, 8, "COLUMN")
        assert any("Input" in line and "5" in line for line in reporting.report_lines)
