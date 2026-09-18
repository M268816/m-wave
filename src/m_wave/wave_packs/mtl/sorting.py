# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiljates.
# All rights reserved
#
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH

# stdlib
import re

# third party
import pandas as pd

# local core
from m_wave.core.reporting import Reporting

# local wave pack
from m_wave.wave_packs.mtl.metadata import Metadata, TableType


class Sorting:
    """
    Helper class that handles all MTL and INPUT CSV sorting methods.
    """

    def __init__(self, report: Reporting, metadata: Metadata) -> None:
        self.report = report
        self.metadata = metadata

    def _handle_element_template_hierarchy(self, df: pd.DataFrame):
        """
        Sorts the element-tempalte records that use logical hierarchy.
        This handles name and parent columns with export paths like:
        ElementTemplates[...]/NotificationRuleTemplates[...]
        ElementTemplates[...]/NotificationRuleTemplates[...]/
        DeliveryFormats[...]
        """

        try:
            type_order: dict = self.metadata.get_group_key_order()  # type: ignore
        except TypeError:
            raise KeyError("Cannot define group order keys. Critical Error.")
        except Exception as e:
            raise RuntimeError(
                f"An unexpected error occurred during group order key retrieval.{e}"
            )

        def as_text(value: object) -> str:
            if pd.isna(value):  # type: ignore
                return ""
            return str(value).strip()

        def bracket_value(path: str, label: str) -> str:
            """
            Extract a value from a key column with an export path.
            """
            match = re.search(
                re.escape(label) + r"\[([^\]]*)]",
                path,
            )
            return match.group(1) if match else ""

        def hierarchy_key(row: pd.Series) -> tuple:
            object_type = as_text(row.get("ObjectType", ""))
            parent = as_text(row.get("Parent", ""))
            name = as_text(row.get("Name", ""))

            if object_type == "ElementTemplate":
                return ((0, name),)

            if object_type in {
                "AttributeTemplate",
                "AnalysisTemplate",
                "NotificationRuleTemplate",
            }:
                root_name = parent.split("\\", 1)[0]

                return (
                    (0, root_name),
                    (type_order[object_type], name),
                )

            if object_type == "TemplateAnalysisRule":
                parent_parts = parent.split("\\")
                root_name = parent_parts[0]
                analysis_name = parent_parts[-1]

                return (
                    (0, root_name),
                    (
                        type_order["AnalysisTemplate"],
                        analysis_name,
                    ),
                    (type_order["TemplateAnalysisRule"], name),
                )
            # Delivery format under its notification rule template
            if object_type == "DeliveryFormat":
                root_name = bracket_value(
                    parent,
                    "ElementTemplates",
                )
                notification_name = bracket_value(
                    parent,
                    "NotificationRuleTemplates",
                )

                return (
                    (0, root_name),
                    (
                        type_order["NotificationRuleTemplate"],
                        notification_name,
                    ),
                    (
                        type_order["DeliveryFormat"],
                        name,
                    ),
                )

            # Delivery-format property under its delivery format
            if object_type == "DeliveryFormatProperty":
                root_name = bracket_value(
                    parent,
                    "ElementTemplates",
                )
                notification_name = bracket_value(
                    parent,
                    "NotificationRuleTemplates",
                )
                delivery_name = bracket_value(
                    parent,
                    "DeliveryFormats",
                )

                return (
                    (0, root_name),
                    (
                        type_order["NotificationRuleTemplate"],
                        notification_name,
                    ),
                    (
                        type_order["DeliveryFormat"],
                        delivery_name,
                    ),
                    (
                        type_order["DeliveryFormatProperty"],
                        name,
                    ),
                )

            # Safe fallback for future object types
            return (
                (999, object_type),
                (999, parent),
                (999, name),
            )

        # Include the original position as a final stable tie-breaker.
        original_positions = range(len(df))

        sorted_positions = sorted(
            original_positions,
            key=lambda position: (
                hierarchy_key(df.iloc[position]),
                position,
            ),
        )

        return df.iloc[sorted_positions].reset_index(drop=True)

    def sort(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Helper function that sorts the data according to the master data table formats.
        Returns an empty data frame if it fails.
        """
        output = pd.DataFrame()
        _df = df.copy()
        try:
            sort_order = self.metadata.get_table_sort_order()
            sort_ascending = self.metadata.get_table_sort_direction()
            group_key = self.metadata.get_group_key()
            group_parent_key = self.metadata.get_group_parent_key()
            group_member_key = self.metadata.get_group_member_key()
            group_key_order = self.metadata.get_group_key_order()

            if (
                group_key_order is not None
                and self.metadata.table_type == TableType.ELEMENT_TEMPLATE
            ):
                self.report.info("Using hierarchical Element Tempalte Sorting.")
                output = self._handle_element_template_hierarchy(_df)
                self.report.info("Hierarchical ElementTemplate sorting completed")
                return output

            if group_key_order is not None:
                self.report.info("Special ordering required.")

                uses_path_sort = self.metadata.use_path_sorting()
                path_sorting_keys = self.metadata.get_path_sorting_keys()

                # Creates a temp numeric ordering column
                _df["group_key_order"] = _df[group_key].map(group_key_order)  # type: ignore
                self.report.info("Created temporary sorting column 'group_key_order'.")

                if uses_path_sort and path_sorting_keys:
                    # Build a full path string for sorting: \Parent\Name
                    self.report.info("Path based sorting detected.")
                    _df["group_key"] = _df[path_sorting_keys].apply(
                        lambda row: "\\".join(
                            str(val)
                            for val in row
                            if pd.notna(val) and str(val).strip() != ""
                        ),
                        axis=1,
                    )
                else:
                    # Ties each member row back to a parent set
                    _df["group_key"] = _df.apply(
                        lambda row: (
                            row[group_parent_key]
                            if row[group_key] == next(iter(group_key_order.keys()))
                            else row[group_member_key]
                        ),
                        axis=1,
                    )
                    self.report.info("Created temporary sorting column 'group_key'.")

            # Sort the data frame
            self.report.info("Sorting...")
            _df = _df.sort_values(
                by=sort_order,
                ascending=sort_ascending,
                ignore_index=True,
                kind="stable",
            )

            # If we used the custom ordering columns, drop them here
            if group_key_order is not None:
                self.report.info("Dropping the sorting column.")
                _df = _df.drop(columns=["group_key_order", "group_key"])

            # Reset the index
            output = _df.reset_index(drop=True)
            self.report.info("Index reset!")
            self.report.info("Sorting completed.")
            return output
        except Exception as e:
            self.report.exception(f"{e}")
            return output
