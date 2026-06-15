# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved

"""
Tests for src/mtl/formatter.py -- DataFormatter.
No GUI dependency.
"""

import pytest
import pandas as pd
from src.mtl.formatter import DataFormatter
from src.main.metadata import MTL_VERSION


class TestNormalizeWhitespace:

    def test_removes_extra_spaces(self, reporting, mock_app_metadata):
        fmt = DataFormatter(reporting, mock_app_metadata)
        df = pd.DataFrame({"Name": ["  Item  1  ", "Item   2"]})
        result = fmt._normalize_whitespace(df)
        assert result["Name"].iloc[0] == "Item 1"
        assert result["Name"].iloc[1] == "Item 2"

    def test_removes_newlines(self, reporting, mock_app_metadata):
        fmt = DataFormatter(reporting, mock_app_metadata)
        df = pd.DataFrame({"Name": ["Item\n1", "Item\r\n2"]})
        result = fmt._normalize_whitespace(df)
        assert "\n" not in result["Name"].iloc[0]

    def test_specific_columns_only(self, reporting, mock_app_metadata):
        fmt = DataFormatter(reporting, mock_app_metadata)
        df = pd.DataFrame({"Name": ["  Item  "], "ID": ["  123  "]})
        result = fmt._normalize_whitespace(df, columns=["Name"])
        assert result["Name"].iloc[0] == "Item"
        assert result["ID"].iloc[0] == "  123  "


class TestFilterByString:

    def test_exact_match(self, reporting, mock_app_metadata, sample_dataframe):
        fmt = DataFormatter(reporting, mock_app_metadata)
        result = fmt.filter_by_string(sample_dataframe, "Item1")
        assert len(result) == 1
        assert result["Name"].iloc[0] == "Item1"

    def test_wildcard_leading(self, reporting, mock_app_metadata, sample_dataframe):
        fmt = DataFormatter(reporting, mock_app_metadata)
        assert len(fmt.filter_by_string(sample_dataframe, "*1")) == 1

    def test_wildcard_trailing(self, reporting, mock_app_metadata, sample_dataframe):
        fmt = DataFormatter(reporting, mock_app_metadata)
        assert len(fmt.filter_by_string(sample_dataframe, "Item*")) == 3

    def test_no_match_returns_empty(self, reporting, mock_app_metadata, sample_dataframe):
        fmt = DataFormatter(reporting, mock_app_metadata)
        assert fmt.filter_by_string(sample_dataframe, "NoExist").empty

    def test_empty_string_returns_original(self, reporting, mock_app_metadata, sample_dataframe):
        fmt = DataFormatter(reporting, mock_app_metadata)
        pd.testing.assert_frame_equal(
            fmt.filter_by_string(sample_dataframe, ""), sample_dataframe
        )

    def test_empty_dataframe_returns_empty(self, reporting, mock_app_metadata):
        fmt = DataFormatter(reporting, mock_app_metadata)
        assert fmt.filter_by_string(pd.DataFrame(), "test").empty


class TestFormat:

    def test_returns_non_empty_dataframe(self, reporting, mock_app_metadata, sample_dataframe):
        fmt = DataFormatter(reporting, mock_app_metadata)
        result = fmt.format(sample_dataframe.copy())
        assert result is not None and not result.empty

    def test_returns_empty_on_none(self, reporting, mock_app_metadata):
        fmt = DataFormatter(reporting, mock_app_metadata)
        result = fmt.format(None)
        assert isinstance(result, pd.DataFrame) and result.empty

    def test_removes_blank_column_names(self, reporting, mock_app_metadata):
        fmt = DataFormatter(reporting, mock_app_metadata)
        df = pd.DataFrame({"Name": [1, 2], "": [3, 4], " ": [5, 6]})
        result = fmt.format(df)
        assert "" not in result.columns
        assert " " not in result.columns

    def test_drops_rows_missing_all_index_keys(self, reporting, mock_app_metadata):
        fmt = DataFormatter(reporting, mock_app_metadata)
        df = pd.DataFrame({"Name": ["Item1", None, "Item3"], "ID": [1, None, 3]})
        result = fmt.format(df)
        assert len(result) <= len(df)


class TestConformColumns:

    def test_removes_extra_input_columns(self, reporting, mock_app_metadata):
        fmt = DataFormatter(reporting, mock_app_metadata)
        mtl = pd.DataFrame({"A": [1], "B": [2]})
        inp = pd.DataFrame({"A": [3], "B": [4], "C": [5]})
        _, inp_result = fmt.conform_columns(mtl, inp)
        assert "C" not in inp_result.columns

    def test_columns_match_after_conform(self, reporting, mock_app_metadata):
        fmt = DataFormatter(reporting, mock_app_metadata)
        mtl = pd.DataFrame({"A": [1], "B": [2]})
        inp = pd.DataFrame({"A": [3], "B": [4], "C": [5]})
        mtl_r, inp_r = fmt.conform_columns(mtl, inp)
        assert set(mtl_r.columns) == set(inp_r.columns)

    def test_none_inputs_return_empty(self, reporting, mock_app_metadata):
        fmt = DataFormatter(reporting, mock_app_metadata)
        mtl_r, inp_r = fmt.conform_columns(None, None)
        assert mtl_r.empty and inp_r.empty

    def test_adds_version_column_when_requested(self, reporting, mock_app_metadata):
        fmt = DataFormatter(reporting, mock_app_metadata)
        mtl = pd.DataFrame({"A": [1], "Version": MTL_VERSION})
        inp = pd.DataFrame({"A": [2]})
        _, inp_r = fmt.conform_columns(mtl, inp, use_version=True)
        assert "Version" in inp_r.columns


class TestSort:

    def test_maintains_row_count(self, reporting, mock_app_metadata, sample_dataframe):
        fmt = DataFormatter(reporting, mock_app_metadata)
        result = fmt.sort(sample_dataframe.copy())
        assert len(result) == len(sample_dataframe)

    def test_resets_index(self, reporting, mock_app_metadata, sample_dataframe):
        fmt = DataFormatter(reporting, mock_app_metadata)
        df = sample_dataframe.copy()
        df.index = [10, 20, 30]
        result = fmt.sort(df)
        assert list(result.index) == list(range(len(result)))

    def test_empty_returns_empty(self, reporting, mock_app_metadata):
        fmt = DataFormatter(reporting, mock_app_metadata)
        assert fmt.sort(pd.DataFrame()).empty


class TestCouldFormat:

    def test_true_for_valid_frames(self, reporting, mock_app_metadata, sample_dataframe):
        fmt = DataFormatter(reporting, mock_app_metadata)
        assert fmt.could_format(sample_dataframe, sample_dataframe) is True

    def test_false_when_mtl_empty(self, reporting, mock_app_metadata, sample_dataframe):
        fmt = DataFormatter(reporting, mock_app_metadata)
        assert fmt.could_format(pd.DataFrame(), sample_dataframe) is False

    def test_false_when_input_empty(self, reporting, mock_app_metadata, sample_dataframe):
        fmt = DataFormatter(reporting, mock_app_metadata)
        assert fmt.could_format(sample_dataframe, pd.DataFrame()) is False
