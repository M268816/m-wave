# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
#
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH

# stdlib
import getpass
import json
from dataclasses import dataclass
from enum import Enum

# local
from src.app.paths import CONFIG_PATH


class TableType(int, Enum):
    UNKNOWN = 0
    ANALYTICS = 1
    DIGITAL_SET = 2
    GXP = 3
    ENUM_SET = 4
    CATEGORIES = 5
    TABLES = 6
    EVENT_FRAME = 7
    ELEMENT_TEMPLATE = 8
    ELEMENT = 9


@dataclass
class TableInfo:
    """
    A data class to hold the named excel table metadata.
    """

    table_id: str
    type: TableType = TableType.UNKNOWN
    can_compare: bool = False


def load_user_config() -> dict:
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise SystemExit(f"Configuration not found. Cannot run application.\n{e}")


_config = load_user_config()

USER = getpass.getuser()

WORKSHEET_METADATA = {
    sheet_name: TableInfo(
        table_id=entry["table_id"],
        type=TableType[entry["type"]],
        can_compare=entry["can_compare"],
    )
    for sheet_name, entry in _config["worksheet_metadata"].items()
}

TABLE_FORMATTING = {
    TableType[key]: {
        "Index Keys": entry["index_keys"],
        "Filter on Keys": entry["filter_on_keys"],
        "Filter Keys": entry["filter_keys"],
        "Object Type Order": entry["object_type_order"],
        "Sort Order": entry["sort_order"],
        "Sort Ascending": entry["sort_ascending"],
    }
    for key, entry in _config["table_formatting"].items()
}

DATAFRAME_FORMATTING = _config["dataframe_formatting"]

DATETIME_FORMAT = "%Y-%m-%dT%H_%M_%SZ"
DATETIME_FORMAT_MERCK = "%d-%b-%Y %H:%M:%S"

MTL_VERSION = _config["mtl_version"]


class AppMetadata:
    """
    Each data class that needs metadata for a worksheet constructs this one instance
    and uses it throughout:

    Usage:
    meta = AppMetadata(worksheet_name)
    keys = meta.get_merge_keys()
    sort = meta.get_sort_order()
    """

    def __init__(self, worksheet_name: str) -> None:
        self.worksheet_name = worksheet_name
        self._table_type = WORKSHEET_METADATA[self.worksheet_name].type

    def get_worksheet_name(self) -> str:
        return self.worksheet_name

    def can_compare_worksheet(self) -> bool:
        return WORKSHEET_METADATA[self.worksheet_name].can_compare

    def get_table_type(self) -> TableType:
        return self._table_type

    def get_table_id(self) -> str:
        return WORKSHEET_METADATA[self.worksheet_name].table_id

    def get_table_formatting(self) -> dict:
        return TABLE_FORMATTING[self._table_type]

    def get_table_index_keys(self) -> list[str]:
        return TABLE_FORMATTING[self._table_type]["Index Keys"]

    def should_filter_on_keys(self) -> bool:
        return TABLE_FORMATTING[self._table_type]["Filter on Keys"]

    def get_table_filter_keys(self) -> list[str]:
        return TABLE_FORMATTING[self._table_type]["Filter Keys"]

    def get_table_sort_order(self) -> list[str]:
        return TABLE_FORMATTING[self._table_type]["Sort Order"]

    def get_table_sort_direction(self) -> list[bool]:
        return TABLE_FORMATTING[self._table_type]["Sort Ascending"]

    def get_table_type_order(self) -> dict | None:
        return TABLE_FORMATTING[self._table_type]["Object Type Order"]
