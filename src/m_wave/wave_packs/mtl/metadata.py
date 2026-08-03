# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
#
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH

# stdlib
import json
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

# local core
from m_wave.core.reporting import Reporting

# local wave pack
from m_wave.wave_packs.mtl.paths import MTL_DOC_DIR, get_mtl_config_path


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


class Metadata:
    def __init__(self, report: Reporting, ws_name: str | None = None) -> None:
        self.report: Reporting = report
        self.worksheet_name = ws_name
        self.mtl_configs = self.get_mtl_configs()
        self.worksheet_metadata = self.get_worksheet_metadata()
        self.table_type: TableType = self.get_table_type()
        self.table_formatting = self.get_table_formatting()
        self.dataframe_formatting = self.get_dataframe_formatting()
        self.mtl_document_path = self.get_mtl_document_path()

    def set_worksheet_name(self, name: str):
        self.worksheet_name = name

    def set_table_type(self):
        self.table_type = self.worksheet_metadata[self.worksheet_name].type

    def worksheet_name_is_set(self) -> bool:
        if self.worksheet_name:
            return True

        self.report.critical("Worksheet name was never set!")
        return False

    def get_mtl_configs(self) -> dict:
        try:
            with open(get_mtl_config_path(), "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            raise SystemExit(f"Configuration not found. Cannot run application.\n{e}")

    def get_worksheet_metadata(self) -> dict:
        return {
            sheet_name: TableInfo(
                table_id=entry["table_id"],
                type=TableType[entry["type"]],
                can_compare=entry["can_compare"],
            )
            for sheet_name, entry in self.mtl_configs["worksheet_metadata"].items()
        }

    def get_table_formatting(self) -> dict:
        return {
            TableType[key]: {
                "Index Keys": entry["index_keys"],
                "Filter on Keys": entry["filter_on_keys"],
                "Filter Keys": entry["filter_keys"],
                "Sort Order": entry["sort_order"],
                "Sort Ascending": entry["sort_ascending"],
                "Group Key": entry.get("group_key"),
                "Group Parent Key": entry.get("group_parent_key"),
                "Group Member Key": entry.get("group_member_key"),
                "Group Key Order": entry.get("group_key_order"),
                "Use Path Sorting": entry.get("use_path_sorting"),
                "Path Sorting Keys": entry.get("path_sorting_keys"),
            }
            for key, entry in self.mtl_configs["table_formatting"].items()
        }

    def get_table_type(self) -> TableType:
        if self.worksheet_name_is_set():
            return self.worksheet_metadata[self.worksheet_name].type
        self.report.critical("Table type could not be set.")
        return TableType.UNKNOWN

    def table_type_is_set(self) -> bool:
        if self.table_type is not None and self.table_type != TableType.UNKNOWN:
            return True

        self.report.critical(
            "Table type was not set before trying to return table data.", popup=True
        )
        return False

    def get_mtl_version(self) -> str:
        return self.mtl_configs["mtl_version"]

    def set_mtl_version(self, new_version: str) -> None:
        try:
            config_path = get_mtl_config_path()
            config = self.get_mtl_configs()
            config["mtl_version"] = new_version
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)
            self.mtl_configs["mtl_version"] = new_version
        except Exception as e:
            self.report.critical("MTL configuration could not be written.", popup=True)
            self.report.exception(f"{e}")

    def get_mtl_doc_num(self) -> str:
        return self.mtl_configs["mtl_doc_num"]

    def get_mtl_document_path(self) -> Path:
        return Path(MTL_DOC_DIR / self.get_mtl_doc_num()).with_suffix(".xlsx")

    def get_mtl_dl_url(self) -> str:
        return self.mtl_configs["mtl_dl_url"]

    def get_dataframe_formatting(self) -> dict:
        return self.mtl_configs["dataframe_formatting"]

    def get_worksheet_name(self) -> str:
        if self.worksheet_name_is_set():
            return self.worksheet_name if self.worksheet_name else "None"
        return "None"

    def can_compare_worksheet(self) -> bool:
        if self.worksheet_name_is_set():
            return self.worksheet_metadata[self.worksheet_name].can_compare
        return False

    def get_table_id(self) -> str:
        if self.worksheet_name_is_set():
            return self.worksheet_metadata[self.worksheet_name].table_id
        return "None"

    def get_formatting_rules(self) -> dict:
        if self.table_type_is_set():
            return self.table_formatting[self.table_type]
        return {}

    def get_table_index_keys(self) -> list[str]:
        if self.table_type_is_set():
            return self.table_formatting[self.table_type]["Index Keys"]
        return []

    def should_filter_on_keys(self) -> bool:
        if self.table_type_is_set():
            return self.table_formatting[self.table_type]["Filter on Keys"]
        return False

    def get_table_filter_keys(self) -> list[str]:
        if self.table_type_is_set():
            return self.table_formatting[self.table_type]["Filter Keys"]
        return []

    def get_table_sort_order(self) -> list[str]:
        if self.table_type_is_set():
            return self.table_formatting[self.table_type]["Sort Order"]
        return []

    def get_table_sort_direction(self) -> list[bool]:
        if self.table_type_is_set():
            return self.table_formatting[self.table_type]["Sort Ascending"]
        return []

    def get_group_key_order(self) -> dict | None:
        if self.table_type_is_set():
            return self.table_formatting[self.table_type]["Group Key Order"]
        return None

    def get_group_key(self) -> str | None:
        if self.table_type_is_set():
            return self.table_formatting[self.table_type]["Group Key"]
        return None

    def get_group_parent_key(self) -> str | None:
        if self.table_type_is_set():
            return self.table_formatting[self.table_type]["Group Parent Key"]
        return None

    def get_group_member_key(self) -> str | None:
        if self.table_type_is_set():
            return self.table_formatting[self.table_type]["Group Member Key"]
        return None

    def use_path_sorting(self) -> bool:
        if self.table_type_is_set():
            return self.table_formatting[self.table_type]["Use Path Sorting"]
        return False

    def get_path_sorting_keys(self) -> list[str]:
        if self.table_type_is_set():
            return self.table_formatting[self.table_type]["Path Sorting Keys"]
        return []

