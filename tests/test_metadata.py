"""
Tests for src/metadata.py - Configuration and metadata handling.
"""

import pytest
from src.metadata import TableType, TableInfo, AppMetadata, WORKSHEET_METADATA


class TestTableType:
    """Tests for TableType enum."""

    def test_table_type_values(self):
        """TableType enum should have expected integer values."""
        assert TableType.UNKNOWN.value == 0
        assert TableType.ANALYTICS.value == 1
        assert TableType.GXP.value == 3

    def test_table_type_cast_from_int(self):
        """TableType should be castable from integer."""
        assert TableType(1) == TableType.ANALYTICS
        assert TableType(3) == TableType.GXP

    def test_invalid_table_type_raises_error(self):
        """Casting invalid integer to TableType should raise ValueError."""
        with pytest.raises(ValueError):
            TableType(999)

    def test_table_type_comparison(self):
        """TableType should support equality comparison."""
        assert TableType.ANALYTICS == TableType.ANALYTICS
        assert TableType.ANALYTICS != TableType.GXP


class TestTableInfo:
    """Tests for TableInfo dataclass."""

    def test_table_info_creation(self):
        """TableInfo should create with required fields."""
        info = TableInfo(
            table_id="test_table",
            type=TableType.ANALYTICS,
            can_compare=True,
        )
        assert info.table_id == "test_table"
        assert info.type == TableType.ANALYTICS
        assert info.can_compare is True

    def test_table_info_default_type(self):
        """TableInfo should default to UNKNOWN type."""
        info = TableInfo(table_id="test_table")
        assert info.type == TableType.UNKNOWN

    def test_table_info_default_can_compare(self):
        """TableInfo should default can_compare to False."""
        info = TableInfo(table_id="test_table")
        assert info.can_compare is False


class TestAppMetadata:
    """Tests for AppMetadata class."""

    @pytest.fixture
    def metadata(self):
        """Get a test metadata instance."""
        # Use first worksheet from actual config
        first_worksheet = next(iter(WORKSHEET_METADATA.keys()))
        return AppMetadata(first_worksheet)

    def test_get_worksheet_name(self, metadata):
        """get_worksheet_name should return the worksheet name."""
        assert isinstance(metadata.get_worksheet_name(), str)
        assert len(metadata.get_worksheet_name()) > 0

    def test_can_compare_worksheet(self, metadata):
        """can_compare_worksheet should return boolean."""
        result = metadata.can_compare_worksheet()
        assert isinstance(result, bool)

    def test_get_table_type(self, metadata):
        """get_table_type should return a TableType."""
        table_type = metadata.get_table_type()
        assert isinstance(table_type, TableType)

    def test_get_table_id(self, metadata):
        """get_table_id should return a string."""
        table_id = metadata.get_table_id()
        assert isinstance(table_id, str)
        assert len(table_id) > 0

    def test_get_table_formatting(self, metadata):
        """get_table_formatting should return a dict with expected keys."""
        formatting = metadata.get_table_formatting()
        assert isinstance(formatting, dict)
        assert "Index Keys" in formatting
        assert "Filter Keys" in formatting
        assert "Sort Order" in formatting

    def test_get_table_index_keys(self, metadata):
        """get_table_index_keys should return a list of strings."""
        keys = metadata.get_table_index_keys()
        assert isinstance(keys, list)
        if keys:
            assert all(isinstance(k, str) for k in keys)

    def test_get_table_filter_keys(self, metadata):
        """get_table_filter_keys should return a list of strings."""
        keys = metadata.get_table_filter_keys()
        assert isinstance(keys, list)
        if keys:
            assert all(isinstance(k, str) for k in keys)

    def test_get_table_sort_order(self, metadata):
        """get_table_sort_order should return a list of strings."""
        order = metadata.get_table_sort_order()
        assert isinstance(order, list)
        if order:
            assert all(isinstance(o, str) for o in order)

    def test_get_table_sort_direction(self, metadata):
        """get_table_sort_direction should return a list of booleans."""
        direction = metadata.get_table_sort_direction()
        assert isinstance(direction, list)
        if direction:
            assert all(isinstance(d, bool) for d in direction)

    def test_invalid_worksheet_raises_error(self):
        """Creating AppMetadata with invalid worksheet should raise KeyError."""
        with pytest.raises(KeyError):
            AppMetadata("INVALID_WORKSHEET")
