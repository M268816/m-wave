# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH
# This tool was created with the help of AI.

# stdlib
import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

# local core
from m_wave.core.reporting.reporter import Reporter

# local extension
from m_wave.extensions.mtl.utils.paths import MTL_DOC_DIR, get_mtl_config_path


class MetadataContextError(RuntimeError):
    """
    Base error for unavailable worksheet or table context.
    """


class WorksheetNotSetError(MetadataContextError):
    """
    Raised when worksheet-specific metadata is requested before selection.
    """


class UnknownWorksheetError(MetadataContextError):
    """
    Raised when the selected worksheet has no configured metadata.
    """


class MetadataConfigurationError(RuntimeError):
    """
    Raised when configuration contains missing or invalid table metadata.
    """


class MissingTableFormattingError(MetadataContextError):
    """
    Raised when a table type has no corresponding formatting configuration.
    """


class TableType(str, Enum):
    ANALYTICS = "analytics"
    DIGITAL_SET = "digital_set"
    GXP = "pi_tags"
    ENUM_SET = "enumeration_set"
    CATEGORIES = "categories"
    TABLES = "tables"
    EVENT_FRAME = "event_frame_templates"
    ELEMENT_TEMPLATE = "element_templates"
    ELEMENT = "elements"


@dataclass
class TableInfo:
    """
    Metadata fora names excel table.
    """

    table_id: str
    type: TableType
    can_compare: bool = False
    permeable_permissions: bool = False
    permeable_permission_values: list[str] | None = None


class Metadata:
    """
    Load MTL Configuration and provide context-aware metadata access.
    """

    def __init__(
        self,
        reporter: Reporter,
        ws_name: str | None = None,
        config_path: Path | None = None,
    ) -> None:
        self.report: Reporter = reporter
        self.journal = reporter.journal
        self.debug = reporter.debug
        self.notify = reporter.notifier

        self.worksheet_name: str | None = None
        self._config_path = Path(config_path or get_mtl_config_path())
        self.mtl_configs: dict[str, Any] = {}

        self.reload_config()

        if ws_name is not None:
            self.set_worksheet_name(ws_name)

    def reload_config(self) -> None:
        """
        Reload the JSON file and refresh all derived configuration attributes.

        This instance holds a snapshot of the file's configuration. Call this
        method to pick up changes made outside this instance.
        """
        configs = self._load_mtl_configs()
        self._apply_config(configs)

    def _load_mtl_configs(self) -> dict[str, Any]:
        """
        Read the configuration JSON file.
        """
        try:
            with self._config_path.open("r", encoding="utf-8") as f:
                configs = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            raise RuntimeError(
                f"Configuration could not be loaded from {self._config_path}"
            ) from e

        if not isinstance(configs, dict):
            raise TypeError(
                f"Configuration at {self._config_path} must contain a JSON object."
            )

        return configs

    def _apply_config(self, configs: dict[str, Any]) -> None:
        """Validate config and refresh this instance's configuration attributes.

        Treat the exposed config attributes as read-only. Use set_mtl_version() or
        reload_config() rather than mutating them directly.
        """
        try:
            mtl_version = configs["mtl_version"]
            mtl_doc_num = configs["mtl_doc_num"]
            mtl_dl_url = configs["mtl_dl_url"]
            val_server = configs["val_server"]
            prod_server = configs["prod_server"]
            mtl_instructions_git_url = configs["mtl_instructions_git_url"]
            mtl_help_vid_url = configs["mtl_help_vid_url"]
            canon_security_string_order = configs["canon_security_string_order"]

            dataframe_formatting = configs["dataframe_formatting"]
            excluded_columns = dataframe_formatting["exclude_columns"]
            security_string_columns = dataframe_formatting["security_string_columns"]
            datetime_columns = dataframe_formatting["datetime_columns"]
            numeric_columns = dataframe_formatting["numeric_columns"]
            classic_gxp_columns = dataframe_formatting["classic_gxp_columns"]

            worksheet_metadata = self._build_worksheet_metadata(
                configs["worksheet_metadata"]
            )
            table_formatting = self._build_table_formatting(configs["table_formatting"])
        except KeyError as exc:
            raise MetadataConfigurationError(
                f"Configuration is missing required key {exc.args[0]!r}."
            ) from exc

        worksheet_types = {info.type for info in worksheet_metadata.values()}
        missing_formatting = worksheet_types - table_formatting.keys()
        if missing_formatting:
            missing_names = ", ".join(
                sorted(table_type.name for table_type in missing_formatting)
            )
            raise MetadataConfigurationError(
                "No table formatting is configured for worksheet table type(s): "
                f"{missing_names}."
            )

        # Keep the loaded JSON and its commonly used values available directly.
        self.mtl_configs = configs
        self.mtl_version: str = mtl_version
        self.mtl_doc_num: str = mtl_doc_num
        self.mtl_dl_url: str = mtl_dl_url
        self.val_server: str = val_server
        self.prod_server: str = prod_server
        self.mtl_instructions_git_url: str = mtl_instructions_git_url
        self.mtl_help_vid_url: str = mtl_help_vid_url
        self.canon_security_string_order: list[str] = canon_security_string_order

        self.dataframe_formatting: dict[str, Any] = dataframe_formatting
        self.excluded_columns: list[str] = excluded_columns
        self.security_string_columns: list[str] = security_string_columns
        self.datetime_columns: list[str] = datetime_columns
        self.numeric_columns: list[str] = numeric_columns
        self.classic_gxp_columns: list[str] = classic_gxp_columns

        self.worksheet_metadata: dict[str, TableInfo] = worksheet_metadata
        self.table_formatting: dict[TableType, dict[str, Any]] = table_formatting
        self.mtl_document_path: Path = (
            Path(MTL_DOC_DIR) / self.mtl_doc_num
        ).with_suffix(".xlsx")

    @staticmethod
    def _build_worksheet_metadata(
        configs: dict[str, dict[str, Any]],
    ) -> dict[str, TableInfo]:
        """
        Convert worksheet entries, requiring a valid configured table type.
        """
        worksheet_metadata: dict[str, TableInfo] = {}

        for sheet_name, entry in configs.items():
            try:
                configured_type = entry["type"]
                table_type = TableType[configured_type]
            except (KeyError, TypeError) as e:
                raise MetadataConfigurationError(
                    f"Worksheet {sheet_name} is missing a valid table type."
                ) from e

            worksheet_metadata[sheet_name] = TableInfo(
                table_id=entry["table_id"],
                type=table_type,
                can_compare=entry["can_compare"],
                permeable_permissions=entry["permeable_permissions"],
                permeable_permission_values=entry["permeable_permission_values"],
            )

        return worksheet_metadata

    @staticmethod
    def _build_table_formatting(
        configs: dict[str, dict[str, Any]],
    ) -> dict[TableType, dict[str, Any]]:
        """
        Convert table formatting entries, rejecting unrecognized table types.
        """
        table_formatting: dict[TableType, dict[str, Any]] = {}

        for configured_type, entry in configs.items():
            try:
                table_type = TableType[configured_type]
            except (KeyError, TypeError) as e:
                raise MetadataConfigurationError(
                    f"Table formatting contains invalid table type {configured_type}"
                ) from e

            table_formatting[table_type] = {
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
                "Security Strings": entry.get("security_strings"),
            }

        return table_formatting

    def set_mtl_version(self, new_version: str) -> None:
        """
        Persist a version change and refresh this instance's config snapshot.
        """
        try:
            configs = self._load_mtl_configs()
            configs["mtl_version"] = new_version

            with self._config_path.open("w", encoding="utf-8") as f:
                json.dump(configs, f, indent=2)

            self._apply_config(configs)
        except (OSError, json.JSONDecodeError, KeyError, TypeError) as e:
            msg = "MTL configuration could not be written"
            self.journal.error(msg)
            self.notify.error(msg)
            self.debug.error(msg + ": %s", e, error=e)

    @property
    def has_worksheet_context(self) -> bool:
        """
        Whether the currently selected worksheet has configured metadata.
        """
        return (
            self.worksheet_name is not None
            and self.worksheet_name in self.worksheet_metadata
        )

    @property
    def worksheet_info(self) -> TableInfo:
        """
        Return the selected worksheet's metadata or raise a context error.
        """
        if self.worksheet_name is None:
            raise WorksheetNotSetError(
                "Set a worksheet name before requesting worksheet metadata."
            )
        try:
            return self.worksheet_metadata[self.worksheet_name]
        except KeyError as e:
            raise UnknownWorksheetError(
                f"No metadata is configured for worksheet {self.worksheet_name}"
            ) from e

    @property
    def table_type(self) -> TableType:
        """
        Return the selected worksheet's configured table type.
        """
        return self.worksheet_info.type

    def set_worksheet_name(self, name: str) -> None:
        """
        Select a configured worksheet; invalid names are rejected immediately.
        """
        if name not in self.worksheet_metadata:
            raise UnknownWorksheetError(
                f"No metadata is configured for worksheet {name}"
            )
        self.worksheet_name = name

    def clear_worksheet_name(self) -> None:
        """
        Clear the worksheet selection, leaving config-only access available.
        """
        self.worksheet_name = None

    def worksheet_name_is_set(self) -> bool:
        """
        Return whether a configured worksheet has been selected.
        """
        return self.worksheet_name is not None

    def table_type_is_set(self) -> bool:
        """
        Return whether a configured worksheet has been selected.
        """
        return self.has_worksheet_context

    def get_table_type(self) -> TableType:
        """
        Return the selected worksheet's table type.
        """
        return self.table_type

    def get_worksheet_name(self) -> str:
        """
        Return the selected worksheet name, requiring a selection.
        """
        if self.worksheet_name is None:
            raise WorksheetNotSetError(
                "Set a worksheet name before requesting its name."
            )
        return self.worksheet_name

    def can_compare_worksheet(self) -> bool:
        """
        Return whether the selected worksheet supports comparison.
        """
        return self.worksheet_info.can_compare

    def get_table_id(self) -> str:
        """
        Return the selected worksheet's Table ID.
        """
        return self.worksheet_info.table_id

    def worksheet_has_permeable_permissions(self) -> bool:
        """
        Return whether the selected worksheet hsa permeable permissions.
        """
        return self.worksheet_info.permeable_permissions

    def get_worksheet_permeable_permission_values(self) -> list[str] | None:
        """
        Return permission values for the selected worksheet.
        """
        return self.worksheet_info.permeable_permission_values

    def _get_current_table_formatting(self) -> dict[str, Any]:
        """
        Return formatting rules for the selected table type.
        """
        table_type = self.table_type
        try:
            return self.table_formatting[table_type]
        except KeyError as e:
            raise MissingTableFormattingError(
                f"No formatting rules are configured for table type {table_type.value}."
            ) from e

    def get_formatting_rules(self) -> dict[str, Any]:
        """
        Return all formatting rules for the selected table type.
        """
        return self._get_current_table_formatting()

    def get_table_index_keys(self) -> list[str]:
        return self._get_current_table_formatting()["Index Keys"]

    def should_filter_on_keys(self) -> bool:
        return bool(self._get_current_table_formatting()["Filter on Keys"])

    def get_table_filter_keys(self) -> list[str]:
        return self._get_current_table_formatting()["Filter Keys"]

    def get_table_sort_order(self) -> list[str]:
        return self._get_current_table_formatting()["Sort Order"]

    def get_table_sort_direction(self) -> list[bool]:
        return self._get_current_table_formatting()["Sort Ascending"]

    def get_group_key_order(self) -> dict[str, Any] | None:
        return self._get_current_table_formatting()["Group Key Order"]

    def get_group_key(self) -> str | None:
        return self._get_current_table_formatting()["Group Key"]

    def get_group_parent_key(self) -> str | None:
        return self._get_current_table_formatting()["Group Parent Key"]

    def get_group_member_key(self) -> str | None:
        return self._get_current_table_formatting()["Group Member Key"]

    def use_path_sorting(self) -> bool:
        return bool(self._get_current_table_formatting()["Use Path Sorting"])

    def get_path_sorting_keys(self) -> list[str]:
        return self._get_current_table_formatting()["Path Sorting Keys"]
