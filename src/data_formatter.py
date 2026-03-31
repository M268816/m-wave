# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
#
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH

# stdlib

# third party
import pandas as pd

# local
from src.metadata import DATAFRAME_FORMATTING, MTL_VERSION, AppMetadata, TableType
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

    def __init__(self, report: Reporting, metadata: AppMetadata) -> None:
        self.report = report
        self.metadata = metadata

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
                    # Replace all white space with a single space
                    df_copy[col] = df_copy[col].str.replace(r"\s+", " ", regex=True)
                    # Strip leading/trailing white space
                    df_copy[col] = df_copy[col].str.strip()

            return df_copy
        except Exception as e:
            error_msg = f"Could not normalize white space:\n{e}"
            self.report.exception(error_msg, popup=True)
            return df

    def _classic_data_check(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Helper function that checks the table type and determines whether or not
        to add classic columns to the table if not already present.
        """
        _df = df.copy()
        table_type = self.metadata.get_table_type()
        classic_columns = set(DATAFRAME_FORMATTING["classic_gxp_columns"])

        if table_type == TableType.GXP:
            if classic_columns.issubset(set(_df.columns)):
                return _df
            else:
                for col in classic_columns:
                    if col not in _df.columns:
                        _df[col] = None
        return _df

    def _drop_na_rows(self, df: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
        """
        Drop rows that do not have proper keys assigned. Most likely picked up from
        bad PI Builder exports or misaligned MTL Tables.
        """
        self.report.info("Dropping possible empty rows.")
        _df = df.copy()
        keys = [this_key for this_key in keys if this_key in _df.columns]

        if not keys:
            return _df

        # for keys with one column, drops any row with an empty value
        if len(keys) == 1:
            _df = _df.dropna(subset=keys)
            return _df
        # for keys with multi columns, keeps rows if at least one value is not empty
        else:
            keep_mask = _df[keys].notna().any(axis=1)
            return _df.loc[keep_mask].copy()

    def format(
        self,
        df: pd.DataFrame | None,
        filter_string: str | None = None,
        use_version: bool = False,
    ) -> pd.DataFrame | None:
        """
        Helper function that formats and sorts data frames for equality comparisons.
        Returns None if an error occurs.
        """
        if df is None:
            self.report.error("There was a problem with formatting the data frame.")
            self.report.error("Cannot format empty DataFrame. Returned None.")
            return None
        table_type = self.metadata.get_table_type()
        index_keys = self.metadata.get_table_index_keys()
        try:
            # inputs need to add the current version
            if use_version:
                if "Version" not in df.columns:
                    df["Version"] = MTL_VERSION
            else:
                df = df.drop(columns=["Version"], errors="ignore")

            # Remove blank columns if they exist
            df = df.drop(
                columns=["", " ", None, "none", "nan", "None"], errors="ignore"
            )

            # Check for classic data points, needed for GXP tables for sure.
            df = self._classic_data_check(df)

            # Setting the table configuration data
            config = self.metadata.get_table_formatting()
            self.report.debug(f"Configuration loaded: {config}", report=False)
            self.report.info(f"Object table type: {table_type.name}")
            self.report.info(f"Filter string: {filter_string}")

            # Filter the data
            if filter_string:
                filter_keys = self.metadata.get_table_filter_keys()
                mask = pd.Series(False, index=df.index)
                for key in filter_keys:
                    if key in df.columns:
                        mask = mask | df[key].str.contains(
                            filter_string, case=False, na=False
                        )
                output = df.loc[mask].copy()
            else:
                # Else just copy the input data frame
                output = df.copy()

            # Setting the object type ordering filter
            type_order = config["Object Type Order"]
            if type_order is not None:
                # Apply the custom ordering column
                output["type_order"] = output["ObjectType"].map(type_order)  # type: ignore

            # TODO: Implement sort by custom path. Name, Parent,  etc. columns can be
            # TODO: concatenated to create path like strings "Parent\Name" for a more
            # TODO: accurate sorting method that follows a lot of the MTL table sorting
            # TODO: formats.

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
            # Remove blank rows
            output = self._drop_na_rows(output, index_keys)
            # Changing these columns to int helps some data comparison errors.
            for column in DATAFRAME_FORMATTING["numeric_columns"]:
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

    def could_format(
        self, mtl_dataframe: pd.DataFrame | None, input_dataframe: pd.DataFrame | None
    ) -> bool:
        if mtl_dataframe is None:
            self.report.highlight_titled_error("MTL data formatting failed.")
            return False
        if input_dataframe is None:
            self.report.highlight_titled_error("Input data formatting failed.")
            return False

        self.report.info("✓ MTL formatted successfully!")
        self.report.info("✓ MTL shape after formatting:")
        self.report.info(f"✓        Rows: {mtl_dataframe.shape[0]}")
        self.report.info(f"✓     Columns: {mtl_dataframe.shape[1]}")
        self.report.info("✓ Input formatted successfully!")
        self.report.info("✓ Input shape after formatting:")
        self.report.info(f"✓        Rows: {input_dataframe.shape[0]}")
        self.report.info(f"✓     Columns: {input_dataframe.shape[1]}")
        return True

    # NOTE: Duplicate of DataComparator._report_shape_differences — keep in sync.
    def _report_shape_differences(self, mtl_dim, input_dim, dimension) -> None:
        """
        Reports row or column count differences between two data frames.
        """
        dimension_plural = f"{dimension}s"

        if mtl_dim == input_dim:
            self.report.info(f"✓ {dimension} counts match!")
        else:
            diff = abs(mtl_dim - input_dim)
            larger, smaller = (
                ("MTL", "Input") if mtl_dim > input_dim else ("Input", "MTL")
            )
            self.report.warning(
                f"{larger} has {diff} more {dimension_plural} than {smaller}"
            )

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
        _mtl = mtl_df.copy()
        _input = input_df.copy()
        mtl_cols = _mtl.shape[1]
        input_cols = _input.shape[1]
        try:
            if mtl_cols != input_cols or (_mtl.dtypes != _input.dtypes).any():
                self.report.highlight_error("Columns do not align!")
                self._report_shape_differences(mtl_cols, input_cols, "COLUMN")
                self.report.warning(
                    "Columns or types may not be aligned and will now be tested and changed."
                )
            else:
                self.report.info("Columns are aligned correctly. Continuing...")
                return _mtl, _input

            # Ensure df data is using the same columns as the mtl
            # by filtering the df columns by the mtl columns
            column_difference = set(_input.columns) ^ set(_mtl.columns)
            if column_difference:
                self.report.warning("The current difference in columns are:")
                for i, col in enumerate(column_difference):
                    self.report.warning(f"    {i}:{col}")
            self.report.info("Aligning columns...")
            _input = _input[_mtl.columns]
            self.report.info("✓ Input data columns have aligned to the MTL columns!")
            self.report.info(f"✓ {len(_mtl.columns)} columns set.")
            self.report.info("Columns used within this comparison:")
            for index, col in enumerate(_input.columns):
                self.report.info(f"    {index}:{col}")
            # Ensure the column data types are the same by matching the input
            # dtypes to the mtl dtypes
            self.report.info("Standardizing data types...")
            self.report.info("Casting Input types to match the MTL columns.")
            for col in _input.columns:
                self.report.debug(f"Casting {col} column.", report=False)
                if col in _mtl.columns:
                    self.report.debug(
                        f"Input type: {_input[col].dtype} changed to MTL type: {_mtl[col].dtype}.",
                        report=False,
                    )
                    _input[col] = _input[col].astype(  # type: ignore
                        _mtl[col].dtype  # type: ignore
                    )
            self.report.info("✓ Data types aligned!")
            return _mtl, _input  # type: ignore
        except KeyError as e:
            error_msg = "✗ Column mismatch: The input file is missing required columns."
            self.report.highlight_titled_error(error_msg)
            self.report.error(error_msg)
            self.report.error(f"\n{e}")
            return None
        except Exception as e:
            self.report.highlight_titled_error("Data alignment failed!")
            self.report.error(f"\n{e}")
            return None
