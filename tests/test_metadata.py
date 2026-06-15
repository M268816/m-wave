# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved

"""
Tests for src/metadata.py -- TableType enum, TableInfo dataclass, AppMetadata.
No GUI dependency.
"""

import pytest
from src.main.metadata import TableType, TableInfo, AppMetadata, WORKSHEET_METADATA


class TestTableType:
    """TableType enum contract."""

    def test_known_values(self):
        assert TableType.UNKNOWN.value == 0
        assert TableType.ANALYTICS.value == 1
        assert TableType.GXP.value == 3

    def test_cast_from_int(self):
        assert TableType(1) == TableType.ANALYTICS
        assert TableType(3) == TableType.GXP

    def test_invalid_int_raises(self):
        with pytest.raises(ValueError):
            TableType(999)

    def test_equality(self):
        assert TableType.ANALYTICS == TableType.ANALYTICS
        assert TableType.ANALYTICS != TableType.GXP


class TestTableInfo:
    """TableInfo dataclass defaults and construction."""

    def test_creation_with_all_fields(self):
        info = TableInfo(table_id="t1", type=TableType.ANALYTICS, can_compare=True)
        assert info.table_id == "t1"
        assert info.type == TableType.ANALYTICS
        assert info.can_compare is True

    def test_default_type_is_unknown(self):
        assert TableInfo(table_id="t1").type == TableType.UNKNOWN

    def test_default_can_compare_is_false(self):
        assert TableInfo(table_id="t1").can_compare is False


class TestAppMetadata:
    """AppMetadata against the first real worksheet entry."""

    @pytest.fixture
    def metadata(self):
        first = next(iter(WORKSHEET_METADATA))
        return AppMetadata(first)

    def test_get_worksheet_name_returns_string(self, metadata):
        assert isinstance(metadata.get_worksheet_name(), str)
        assert metadata.get_worksheet_name()

    def test_can_compare_returns_bool(self, metadata):
        assert isinstance(metadata.can_compare_worksheet(), bool)

    def test_get_table_type_returns_table_type(self, metadata):
        assert isinstance(metadata.get_table_type(), TableType)

    def test_get_table_id_returns_non_empty_string(self, metadata):
        tid = metadata.get_table_id()
        assert isinstance(tid, str) and tid

    def test_get_table_formatting_has_required_keys(self, metadata):
        fmt = metadata.get_table_formatting()
        assert isinstance(fmt, dict)
        for key in ("Index Keys", "Filter Keys", "Sort Order"):
            assert key in fmt

    def test_get_table_index_keys_returns_list_of_strings(self, metadata):
        keys = metadata.get_table_index_keys()
        assert isinstance(keys, list)
        assert all(isinstance(k, str) for k in keys)

    def test_get_table_filter_keys_returns_list_of_strings(self, metadata):
        keys = metadata.get_table_filter_keys()
        assert isinstance(keys, list)
        assert all(isinstance(k, str) for k in keys)

    def test_get_table_sort_order_returns_list_of_strings(self, metadata):
        order = metadata.get_table_sort_order()
        assert isinstance(order, list)
        assert all(isinstance(o, str) for o in order)

    def test_get_table_sort_direction_returns_list_of_bools(self, metadata):
        dirs = metadata.get_table_sort_direction()
        assert isinstance(dirs, list)
        assert all(isinstance(d, bool) for d in dirs)

    def test_invalid_worksheet_raises_key_error(self):
        with pytest.raises(KeyError):
            AppMetadata("INVALID_WORKSHEET_XYZ")
