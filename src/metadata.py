# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
#
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH

# stdlib
import json
from dataclasses import dataclass
from enum import Enum

# local
from src.paths import CONFIG_PATH

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    _config = json.load(f)


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
    A data class to hold the excel table name metadata.
    """

    table_id: str
    type: TableType = TableType.UNKNOWN
    can_process: bool = False


WORKSHEET_METADATA = {
    sheet_name: TableInfo(
        table_id=entry["table_id"],
        type=TableType[entry["type"]],
        can_process=entry["can_process"],
    )
    for sheet_name, entry in _config["worksheet_metadata"].items()
}

TABLE_FORMATTING = {
    TableType[key]: {
        "Object Type Order": entry["object_type_order"],
        "Sort Order": entry["sort_order"],
        "Sort Direction": entry["sort_direction"],
    }
    for key, entry in _config["table_formatting"].items()
}

DATAFRAME_FORMATTING = _config["dataframe_formatting"]

DATETIME_FORMAT = "%Y-%m-%dT%H_%M_%SZ"

MTL_VERSION = _config["mtl_version"]
