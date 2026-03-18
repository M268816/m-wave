# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
#
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH

# stdlib

# third party
import pandas as pd

# local
from src.metadata import (
    DATAFRAME_FORMATTING,
    TABLE_FORMATTING,
    WORKSHEET_METADATA,
    TableType,
)
from src.reporting import Reporting


_VALUE_NORMALIZATION_MAP: dict = {
    "TRUE": True,
    "True": True,
    "true": True,
    "FALSE": False,
    "False": False,
    "false": False,
    "": None,
    " ": None,
    "None": None,
    "NULL": None,
    "null": None,
    "NaN": None,
    "nan": None,
}


class DataFormatter:
    """
    Helper class that handles all MTL and INPUT CSV formatting.
    """

    def __init__(self, report: Reporting) -> None:
        self.report = report
        self.worksheet_metadata = WORKSHEET_METADATA
        self.table_formatting = TABLE_FORMATTING
        self.dataframe_formatting = DATAFRAME_FORMATTING

    def _normalize_whitespace(
        self, df: pd.DataFrame, columns: list[str] | None = None
    ) -> pd.DataFrame:
        """
        Aggressively normalize white space - removes all extra spaces and newlines.
        """
        try:
            df_copy = df.copy()

            if columns is None:
                columns = df_copy.select_dtypes(
                    include=["object", "string"]
                ).columns.tolist()
            for col in columns:  # type: ignore
                if col in df_copy.columns:
                    # Replace all whitespace with a single space
                    df_copy[col] = df_copy[col].str.replace(r"\s+", " ", regex=True)
                    # Strip leading/trailing whitespace
                    df_copy[col] = df_copy[col].str.strip()

            return df_copy
        except Exception as e:
            error_msg = f"Could not normalize white space:\n{e}"
            self.report.exception(error_msg, popup=True)
            return df

    def _classic_data_check(
        self, df: pd.DataFrame, table_type: TableType
    ) -> pd.DataFrame:
        """
        Helper function that checks the table type and determines whether or not
        to add classic columns to the table if not already present.
        """
        _df = df.copy()
        classic_columns = set(self.dataframe_formatting["classic_gxp_columns"])
        if table_type == TableType.GXP:
            if classic_columns.issubset(set(_df.columns)):
                return _df
            else:
                for col in classic_columns:
                    if col not in _df.columns:
                        _df[col] = None
        return _df

    def format(
        self,
        table_type: TableType,
        df: pd.DataFrame | None,
        name_filter: str | None = None,
    ) -> pd.DataFrame | None:
        """
        Helper function that formats and sorts data frames for equality comparisons.
        Returns None if an error occurs.
        """
        if df is None:
            self.report.error("There was a problem with formatting the data frame.")
            self.report.error("Cannot format empty DataFrame. Returned None.")
            return None
        name_filter = name_filter or None
        try:
            # self.report.info("Formatting MTL dataframe...")
            # Remove version column if it exists
            df = df.drop(columns=["Version"], errors="ignore")
            # Check for classic data points, needed for GXP for sure.
            df = self._classic_data_check(df, table_type)
            # Setting the table configuration data
            config = self.table_formatting[table_type]
            self.report.debug(f"Configuration loaded: {config}")
            self.report.info(f"Object table type: {table_type.name}")
            self.report.info(f"Object name filter: {name_filter}")
            # Setting the object type ordering filter
            type_order = config["Object Type Order"]
            if name_filter:
                if table_type == TableType.ELEMENT:
                    # Filter mask includes name and template columns
                    mask = df["Name"].str.contains(
                        name_filter, case=False, na=False
                    ) | df["Template"].str.contains(name_filter, case=False, na=False)
                elif table_type in (
                    TableType.GXP,
                    TableType.CATEGORIES,
                    TableType.ANALYTICS,
                ):
                    mask = df["Name"].str.contains(name_filter, case=False, na=False)
                else:
                    # Else, just check the name column and parent
                    mask = df["Name"].str.contains(
                        name_filter, case=False, na=False
                    ) | df["Parent"].str.contains(name_filter, case=False, na=False)
                # Applying the name filter here
                output = df.loc[mask].copy()
            else:
                # Else just copy the input data frame
                output = df.copy()
            if type_order is not None:
                # Apply the custom ordering column
                output["type_order"] = output["ObjectType"].map(type_order)  # type: ignore
            # Sort the data frame
            output = output.sort_values(
                by=config["Sort Order"],
                ascending=config["Sort Direction"],
                ignore_index=True,
                kind="stable",
            )
            # If we used the custom ordering column, drop it here
            if type_order is not None:
                output = output.drop(columns=["type_order"])
            # Reset the index
            output = output.reset_index(drop=True)
            # Changing these columns to int helps some data comparison errors.
            for column in self.dataframe_formatting["numeric_columns"]:
                if column in output.columns:
                    # Convert strings to numbers
                    converted_vals = pd.to_numeric(output[column], errors="coerce")
                    # Convert back to strings
                    output[column] = converted_vals.apply(  # type: ignore
                        lambda x: (
                            str(int(x))
                            if pd.notna(x) and x == int(x)
                            else (str(x) if pd.notna(x) else "0")
                        )
                    )
            # Replace here to standardize bools and blanks
            output = output.replace(_VALUE_NORMALIZATION_MAP)

            # Change everything to strings for faster comparisons
            output = output.astype("string")
            output = self._normalize_whitespace(output)
            return output
        except Exception as e:
            error_msg = f"Could not format dataframe:\n{e}"
            self.report.exception(error_msg, popup=True)
            return None

    def conform_columns(
        self, mtl_df: pd.DataFrame | None, input_df: pd.DataFrame | None
    ) -> tuple[pd.DataFrame, pd.DataFrame] | None:
        """
        A function that attempts to conform the input data frame columns to match the
        MTL data frame columns for comparison.
        Returns None if it fails.
        """
        if mtl_df is None or input_df is None:
            self.report.error("There was a problem conforming the data frames.")
            self.report.error("Cannot conform empty data frames.")
            return None
        mtl = mtl_df.copy()
        df = input_df.copy()
        try:
            # Ensure df data is using the same columns as the mtl
            # by filtering the df columns by the mtl columns
            self.report.info("Aligning columns...")
            df = df[mtl.columns]
            self.report.info("✓ Input data columns have aligned to the MTL columns!")
            self.report.info(f"✓ {len(mtl.columns)} columns set.")

            # Ensure the column data types are the same by matching the input
            # dtypes to the mtl dtypes
            self.report.info("Standardizing data types...")
            self.report.info("Casting Input types to match the MTL columns.")
            for col in df.columns:
                self.report.debug(f"Casting {col} column.")
                if col in mtl.columns:
                    self.report.debug(
                        f"Input type: {df[col].dtype} changed to MTL type: {mtl[col].dtype}."
                    )
                    df[col] = df[col].astype(  # type: ignore
                        mtl[col].dtype  # type: ignore
                    )
            self.report.info("✓ Data types aligned!")
            return mtl, df  # type: ignore
        except KeyError as e:
            error_msg = (
                f"✗ Column mismatch: The input file is missing required columns.\n{e}"
            )
            self.report.highlight_titled_error(error_msg)
            self.report.error(error_msg)
            self.report.save_report()
            return None
        except Exception as e:
            self.report.highlight_titled_error(f"✗ Data alignment failed:\n{e}")
            self.report.save_report()
            return None
