# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
#
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH

# stdlib
import re

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
                self.report.info("Classic columns found.")
                return _df
            else:
                for col in classic_columns:
                    if col not in _df.columns:
                        _df[col] = None
                self.report.info("Classic columns applied.")
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

    def filter_on_keys(
        self, mtl_df: pd.DataFrame, input_df: pd.DataFrame
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Helper function that filters data to the column keys.
        Returns a tuple of data frames. Comparable, and non comparable rows.
        Returns a empty data frames if it fails.
        """
        output = (pd.DataFrame(), pd.DataFrame())
        try:
            # get column keys
            keys = self.metadata.get_table_index_keys()
            original_columns = mtl_df.columns

            # create keyed data frames
            keyed_mtl = mtl_df.set_index(keys)
            keyed_input = input_df.set_index(keys)

            # filter the mtl down to rows that can be compared with the input
            # ie. rows that match the input keys
            comparable_mtl = keyed_mtl[
                keyed_mtl.index.isin(keyed_input.index)
            ].reset_index()[original_columns]

            comparable_input = keyed_input[
                keyed_input.index.isin(keyed_mtl.index)
            ].reset_index()[original_columns]

            # input keys not present in the MTL
            non_comparable = keyed_input[
                ~keyed_input.index.isin(keyed_mtl.index)
            ].reset_index()[original_columns]

            # Save each data frame to keep a record
            comparable_mtl.to_csv(
                self.report.report_folder / "comparable_rows.csv", index=False
            )
            non_comparable.to_csv(
                self.report.report_folder / "non_comparable_rows.csv", index=False
            )

            output = (comparable_mtl, comparable_input)
            return output  # type: ignore

        except KeyError as e:
            error_msg = f"A key error occurred during upserting.\n{e}"
            self.report.exception(error_msg)
            return output
        except ValueError as e:
            error_msg = f"A value error occurred during upserting.\n{e}"
            self.report.exception(error_msg)
            return output
        except Exception as e:
            error_msg = f"An unexpected error occurred during upserting.\n{e}"
            self.report.exception(error_msg)
            return output

    def _mask_to_regex(self, mask: str) -> str:
        """
        Convert an Aveva Pi Builder style filter mask using '*' wildcards into
        a regular expression.
        *FILTER* -> contains the filter
        *FILTER -> ends with the filter
        FILTER* -> starts with the filter
        *A*B* -> A before B
        A*B -> starts with A, ends with B
        """
        reg_mask = (mask or "").strip()

        escaped = "".join(".*" if c == "*" else re.escape(c) for c in reg_mask)
        return f"^{escaped}$"

    # TEST:
    def filter_by_string(
        self,
        df: pd.DataFrame,
        filter_string: str | None = None,
        case_sensitive: bool = False,
        filter_na: bool = False,
    ) -> pd.DataFrame:
        output = pd.DataFrame()
        try:
            if df.empty:
                self.report.error(
                    "The process passed an empty data frame through the filtering process."
                )
                self.report.error("Cannot filter empty data frames. Process failed.")
                return output

            table_type = self.metadata.get_table_type()

            self.report.info(f"Filtering table: {table_type.name}")

            if not filter_string:
                return df.copy()

            self.report.info(f"Filtering by: {filter_string}")
            filter_keys = self.metadata.get_table_filter_keys()
            filter_keys = [key for key in filter_keys if key in df.columns]

            if not filter_keys:
                self.report.warning(
                    "No filter keys found in dataframe; returning unfiltered data frame."
                )
                return df.copy()

            regex_pattern = self._mask_to_regex(filter_string)
            mask = pd.Series(False, index=df.index)

            self.report.debug(f"regex_pattern type: {type(regex_pattern)}")
            self.report.debug(f"regex_pattern representation: {regex_pattern!r}")
            for key in filter_keys:
                as_string = df[key].astype("string")
                mask = mask | as_string.str.match(
                    regex_pattern,
                    case=case_sensitive,
                    na=filter_na,  # flags=re.DOTALL
                )

            output = df.loc[mask].copy()
            self.report.info("Filter applied!")
            return output
        except Exception as e:
            e = str(e)
            self.report.exception(e)
            return output

    # def filter(
    #     self, df: pd.DataFrame | None, filter_string: str | None = None
    # ) -> pd.DataFrame:
    #     """
    #     Helper function that filters the data to the user's filter string.
    #     Returns an empty data frame if it fails.
    #     """
    #     output = pd.DataFrame()
    #     try:
    #         if df is None:
    #             self.report.error("There was a problem filtering the data frame.")
    #             self.report.error(
    #                 "Cannot filter an empty data frame."
    #             )  # Filter the data
    #             return pd.DataFrame()
    #
    #         table_type = self.metadata.get_table_type()
    #
    #         self.report.info(f"Filtering Table: {table_type.name}")
    #         self.report.info(f"Filtering by: {filter_string}")
    #
    #         if filter_string:
    #             filter_keys = self.metadata.get_table_filter_keys()
    #             mask = pd.Series(False, index=df.index)
    #             for key in filter_keys:
    #                 if key in df.columns:
    #                     mask = mask | df[key].str.contains(
    #                         filter_string, case=False, na=False
    #                     )
    #             output = df.loc[mask].copy()
    #         else:
    #             # Else just copy the input data frame
    #             output = df.copy()
    #
    #         self.report.info("Filter applied")
    #         return output
    #
    #     except Exception as e:
    #         self.report.error(f"{e}")
    #         return output

    # TEST: END

    def sort(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Helper function that sorts the data according to the master data table formats.
        Returns an empty data frame if it fails.
        """
        output = pd.DataFrame()
        try:
            # Setting the object type ordering filter
            config = self.metadata.get_table_formatting()
            type_order = config["Object Type Order"]
            if type_order is not None:
                self.report.info("Special ordering required.")
                # Apply the custom ordering column
                df["type_order"] = df["ObjectType"].map(type_order)  # type: ignore
                self.report.info("Created temporary sorting column 'type_order'.")

            # Sort the data frame
            self.report.info("Sorting...")
            df = df.sort_values(
                by=config["Sort Order"],
                ascending=config["Sort Direction"],
                ignore_index=True,
                kind="stable",
            )

            # If we used the custom ordering column, drop it here
            if type_order is not None:
                self.report.info("Dropping the sorting column.")
                df = df.drop(columns=["type_order"])

            # Reset the index
            output = df.reset_index(drop=True)
            self.report.info("Index reset!")
            self.report.info("Sorting completed.")
            return output
        except Exception as e:
            self.report.exception(f"{e}")
            return output

    def format(
        self,
        df: pd.DataFrame | None,
    ) -> pd.DataFrame:
        """
        Helper function that universally formats the cell values to strings for
        data comparison.
        Returns an empty data frame if it fails.
        """
        output = pd.DataFrame()
        if df is None:
            self.report.error("There was a problem with formatting the data frame.")
            self.report.error("Cannot format empty DataFrame. Returned None.")
            return pd.DataFrame()
        index_keys = self.metadata.get_table_index_keys()
        try:
            # Remove blank columns if they exist
            df = df.drop(
                columns=["", " ", None, "none", "nan", "None"], errors="ignore"
            )
            df = df.drop(
                columns=[
                    col
                    for col in df.columns
                    if isinstance(col, str) and "unnamed" in col.lower()
                ],
                errors="ignore",
            )

            # Remove blank rows if they exist
            df = self._drop_na_rows(df, index_keys)

            # Changing these columns to int, helps some data comparison errors.
            for column in DATAFRAME_FORMATTING["numeric_columns"]:
                if column in df.columns:
                    # Convert strings to numbers
                    converted_vals = pd.to_numeric(df[column], errors="coerce")
                    # Convert back to strings
                    df[column] = converted_vals.apply(  # type: ignore
                        lambda x: (
                            str(int(x))
                            if pd.notna(x) and x == int(x)
                            else (str(x) if pd.notna(x) else "0")
                        )
                    )

            # Replace to standardize bools and blanks to python types
            df = df.replace(_VALUE_NORMALIZATION_MAP)

            df = df.astype("string")

            output = self._normalize_whitespace(df)

            return output

        except Exception as e:
            error_msg = f"Could not format dataframe:\n{e}"
            self.report.exception(error_msg, popup=True)
            return output

    def could_format(
        self, mtl_dataframe: pd.DataFrame, input_dataframe: pd.DataFrame
    ) -> bool:
        """
        Checks data frames and returns a bool if they could be formatted.
        """
        if mtl_dataframe.empty:
            self.report.highlight_titled_error("MTL data formatting failed.")
            return False
        if input_dataframe.empty:
            self.report.highlight_titled_error("Input data formatting failed.")
            return False
        self.report.info("MTL formatted successfully!")
        self.report.info("MTL shape after formatting:")
        self.report.info(f"       Rows: {mtl_dataframe.shape[0]}")
        self.report.info(f"    Columns: {mtl_dataframe.shape[1]}")
        self.report.info("Input formatted successfully!")
        self.report.info("Input shape after formatting:")
        self.report.info(f"       Rows: {input_dataframe.shape[0]}")
        self.report.info(f"    Columns: {input_dataframe.shape[1]}")
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
        self,
        mtl_df: pd.DataFrame | None,
        input_df: pd.DataFrame | None,
        use_version: bool = False,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        A function that attempts to conform the input data frame columns to match the
        MTL data frame columns for comparison.
        Returns empty data frames if it fails.
        """

        if mtl_df is None or input_df is None:
            self.report.error("There was a problem conforming the columns.")
            self.report.error("Cannot conform empty data frames.")
            return pd.DataFrame(), pd.DataFrame()
        _mtl = mtl_df.copy()
        _input = input_df.copy()
        output = (pd.DataFrame(), pd.DataFrame())
        try:
            if use_version:
                if "Version" not in _input.columns:
                    _input["Version"] = MTL_VERSION
            else:
                _input = _input.drop(columns=["Version"], errors="ignore")
                _mtl = _mtl.drop(columns=["Version"], errors="ignore")

            mtl_cols = _mtl.shape[1]
            input_cols = _input.shape[1]

            self.report.info("Checking input for classic MTL columns.")
            _input = self._classic_data_check(_input)

            if mtl_cols != input_cols or (_mtl.dtypes != _input.dtypes).any():
                self.report.highlight_error("Columns do not align!")
                self._report_shape_differences(mtl_cols, input_cols, "COLUMN")
                self.report.warning(
                    "Columns or types may not be aligned and will now be tested and changed."
                )
            else:
                self.report.info("Columns are aligned correctly. Continuing...")
                output = (_mtl, _input)
                return output

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
            self.report.info("Data types aligned!")

            output = (_mtl, _input)
            return output  # type: ignore

        except KeyError as e:
            error_msg = "Column mismatch: The input file is missing required columns."
            self.report.highlight_titled_error(error_msg)
            self.report.exception(f"\n{e}\n")
            return output
        except Exception as e:
            self.report.highlight_titled_error("Data alignment failed!")
            self.report.exception(f"\n{e}\n")
            return output
