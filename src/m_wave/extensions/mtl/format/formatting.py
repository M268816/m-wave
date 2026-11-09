# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH
# This tool was created with the help of AI.

# stdlib
import math
import re

# third party
import numpy as np
import pandas as pd

# local core
from m_wave.core.reporting.debug_log import DebugLog
from m_wave.core.reporting.journal import Journal
from m_wave.core.reporting.notifier import Notifier
from m_wave.core.reporting.reporter import Reporter
from m_wave.core.utils import DATETIME_FORMAT_MERCK

# local extension
from m_wave.extensions.mtl.pdf_template import ReportIssue
from m_wave.extensions.mtl.utils.metadata import Metadata, TableType
from m_wave.extensions.mtl.utils.utils import report_shape_differences

_VALUE_NORMALIZATION_MAP: dict = {
    "TRUE": "True",
    "True": "True",
    "true": "True",
    "FALSE": "False",
    "False": "False",
    "false": "False",
    "": pd.NA,
    " ": pd.NA,
}


class Formatting:
    """
    Helper class that handles all MTL and INPUT CSV formatting.
    """

    def __init__(self, reporter: Reporter, metadata: Metadata) -> None:
        self.reporter: Reporter = reporter
        self.journal: Journal = reporter.journal
        self.notify: Notifier = reporter.notifier
        self.debug: DebugLog = reporter.debug
        self.metadata: Metadata = metadata

        # NOTE: use .clear() to reset issues after each run
        self.report_issues: list[ReportIssue] = []

    def filter_on_keys(
        self, mtl_df: pd.DataFrame, input_df: pd.DataFrame
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Helper function that filters data to the MTL column keys.
        Drops PI Builder input columns to match the MTL.
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
            self.reporter.artifacts.save_csv(
                "comparable_rows",
                comparable_mtl,
                "Rows of the MTL/CMD data table that can be compared.",
            )
            self.reporter.artifacts.save_csv(
                "non_comparable_rows",
                non_comparable,
                "Rows of the MTL/CMS data table that cannot be compared.",
            )

            output = (comparable_mtl, comparable_input)
            return output  # type: ignore

        except KeyError as e:
            error_msg = f"A key error occurred during upserting.\n{e}"
            self.journal.error(error_msg)
            self.debug.debug("A key error occurred during upserting.\n %s", e)
            return output
        except ValueError as e:
            error_msg = f"A value error occurred during upserting.\n{e}"
            self.journal.error(error_msg)
            self.debug.debug("A value error occurrred during upserting.\n %s", e)
            return output
        except Exception as e:
            error_msg = f"An unexpected error occurred during upserting.\n{e}"
            self.journal.error(error_msg)
            self.debug.debug("An unexpected error occurred during upserting.\n %s", e)
            return output

    def _mask_to_regex(self, mask: str) -> str:
        """
        Convert an Aveva Pi Builder style filter mask using '*' wild cards into a
        regular expression.

        *FILTER* -> contains the filter
        *FILTER -> ends with the filter
        FILTER* -> starts with the filter
        *A*B* -> A before B
        A*B -> starts with A, ends with B
        """
        reg_mask = (mask or "").strip()

        escaped = "".join(".*" if c == "*" else re.escape(c) for c in reg_mask)
        return f"^{escaped}$"

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
                issue = ReportIssue(
                    "Cannot filter empty data frame.",
                    "Attempted to filter by a string, but cannot filter with an empty data frame.",
                    "Warning",
                )
                self.report_issues.append(issue)
                self.journal.error(
                    "The process passed an empty data frame through the filtering process."
                )
                self.journal.error("Cannot filter empty data frames. Process failed.")
                return output

            table_type = self.metadata.table_type

            self.journal.info(f"Filtering table: {table_type.name}")

            if not filter_string:
                return df.copy()

            self.journal.info(f"Filtering by: {filter_string}")
            filter_keys = self.metadata.get_table_filter_keys()
            filter_keys = [key for key in filter_keys if key in df.columns]

            if not filter_keys:
                self.journal.warning(
                    "No filter keys found in dataframe; returning unfiltered data frame."
                )
                return df.copy()

            regex_pattern = self._mask_to_regex(filter_string)
            mask = pd.Series(False, index=df.index)

            self.debug.debug("regex_pattern type: %s", type(regex_pattern))
            self.debug.debug(
                "regex_pattern representation: %s",
                f"{regex_pattern!r}",
            )
            for key in filter_keys:
                as_string = df[key].astype("string")
                mask = mask | as_string.str.match(
                    regex_pattern,
                    case=case_sensitive,
                    na=filter_na,
                )

            output = df.loc[mask].copy()
            self.journal.info("Filter applied!")
            return output
        except Exception as e:
            self.debug.error("Unexpected error while filtering by string:\n %s", e)
            return output

    def _drop_na_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Remove columns from the dataframe that have null values.
        """
        try:
            _df = df.copy()
            _df = _df.drop(
                columns=["", " ", None, "none", "nan", "None"], errors="ignore"
            )
            _df = _df.drop(
                columns=[
                    col
                    for col in _df.columns
                    if isinstance(col, str) and "unnamed" in col.lower()
                ],
                errors="ignore",
            )
            return _df
        except Exception as e:
            self.debug.error("Unexpected error while dropping na columns:\n %s", e)
            return df

    def _drop_na_rows(self, df: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
        """
        Drop rows that do not have proper keys assigned. Most likely picked up from
        bad PI Builder exports or misaligned MTL Tables.
        """
        self.journal.info("Dropping possible empty rows.")
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

    def _conform_datetime_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Format helper to handle datetime columns, helps some data comparison errors.
        Returns a dataframe.
        """
        try:
            _df = df.copy()
            datetime_columns = self.metadata.dataframe_formatting.get(
                "datetime_columns", []
            )
            for column in datetime_columns:
                if column in _df.columns:
                    col_dtype = _df[column].dtype
                    if pd.api.types.is_float_dtype(
                        col_dtype
                    ) or pd.api.types.is_integer_dtype(col_dtype):
                        # Not a string, cast from date serial to string
                        self.debug.debug(
                            "Converting QA date serial in '%s' to string.", column
                        )

                        _df[column] = (
                            pd.to_datetime(
                                _df[column],
                                unit="D",
                                origin="1899-12-30",
                                errors="coerce",
                            )
                            .dt.strftime(DATETIME_FORMAT_MERCK)
                            .fillna("")
                        )
                    else:
                        # Already a string - normalize to merck standard
                        _df[column] = (
                            pd.to_datetime(_df[column], errors="coerce")
                            .dt.strftime(DATETIME_FORMAT_MERCK)
                            .fillna("")
                        )
            return _df
        except Exception as e:
            self.journal.error(f"Could not format datetime columns:\n {e}")
            self.debug.debug("Could not format datetime columns:\n %s", e)
            return pd.DataFrame()

    def _conform_numeric_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Format helper that changes columns to int, helps some data comparison errors.

        These columns are mostly numeric, but may contain boolean and string
        values.

        Boolean and null values should be normalized and strigified.
          true = True = "True"

        Numerics should keep their values stringified.
          13.2 = "13.2", 12 = "12"

        Any numeric equal to 0 should be stringified to "0".
          0.0 = 0 = "0"

        Other Strings should remain as strings.
        """
        try:
            _df = df.copy()
            numeric_columns = self.metadata.dataframe_formatting["numeric_columns"]

            for column in numeric_columns:
                if column not in _df.columns:
                    continue

                def normalize_cell(x):
                    # Convert possible numeric column values to the normalization map,
                    # or a stringified number, unless its NA, then
                    # keep or convert the value to pd.NA
                    if pd.isna(x):
                        return pd.NA

                    if isinstance(x, (bool, np.bool_)):
                        return "True" if bool(x) else "False"

                    if isinstance(x, str):
                        normal_text = x.strip()

                        if normal_text == "":
                            return pd.NA

                        if normal_text in _VALUE_NORMALIZATION_MAP:
                            return _VALUE_NORMALIZATION_MAP[normal_text]
                    else:
                        normal_text = str(x).strip()

                    numeric_value = pd.to_numeric(x, errors="coerce")

                    if pd.notna(numeric_value):
                        numeric_value = float(numeric_value)  # type: ignore

                        if numeric_value == 0:
                            return "0"

                        if math.isfinite(numeric_value) and numeric_value.is_integer():
                            return str(int(numeric_value))

                    return str(x)

                _df[column] = _df[column].map(normalize_cell)
            return _df
        except Exception as e:
            self.journal.error(f"Could not normalize numeric columns: {e}")
            self.debug.error("Could not normalize number columns:\n %s", e)
            return df

    def _conform_blank_cells(
        self, df: pd.DataFrame, index_keys: list[str]
    ) -> pd.DataFrame:
        """
        Conform excel and csv blank cells to pd.NA, but not indexed columns.
        """
        try:
            _df = df.copy()

            for column in _df.columns:
                if column in index_keys:
                    continue

                values = _df[column]

                missing_mask = values.isna()

                blank_string_mask = (
                    values.astype("string").str.strip().eq("").fillna(False)
                )

                _df[column] = values.mask(
                    missing_mask | blank_string_mask,
                    pd.NA,
                )

            return _df

        except Exception as e:
            self.journal.error(f"Could not conform blank cells: {e}")
            self.debug.error("Could not conform blank cells:\n %", e)
            return df

    def _normalize_key_columns(self, df: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
        """
        Normalizes blank keys to the pandas standard pd.NA while perserving literal
        key values like "N/A", "None", and "Null", which may be valid names
        within key groups.
        """
        try:
            result = df.copy()

            for key in keys:
                if key not in result.columns:
                    self.journal.error_banner(f"{key} not found for key normaliztion.")
                    self.journal.error(f"Columns: {result.columns.tolist()}")
                    continue

                values = (
                    result[key]
                    .astype("string")
                    .str.replace(r"\s+", " ", regex=True)
                    .str.strip()
                )

                result[key] = values.mask(values.eq(""), pd.NA)

            return result

        except Exception as e:
            self.journal.error(f"Could not normalize key columns: {e}")
            self.debug.error("Could not normalize key columns:\n %s", e)
            return df

    def _normalize_whitespace(
        self, df: pd.DataFrame, columns: list[str] | None = None
    ) -> pd.DataFrame:
        """
        Aggressively normalize white space - removes all extra spaces and newlines.
        This could break again because im not pushing all cell values to strings anymore.
        """
        try:
            df_copy = df.copy()

            if columns is None:
                columns = [
                    col
                    for col in df_copy.columns
                    if pd.api.types.is_string_dtype(df_copy[col])
                    or df_copy[col].dtype == "object"
                ]

            for col in columns:
                if col not in df_copy.columns:
                    continue

                values = df_copy[col].dropna()
                if values.map(lambda v: v is True or v is False).any():
                    continue

                df_copy[col] = (
                    df_copy[col]
                    .astype("string")
                    .str.replace(r"\s+", " ", regex=True)
                    .str.strip()
                )
            return df_copy
        except Exception as e:
            error_msg = f"Could not normalize white space:\n{e}"
            self.journal.error(error_msg)
            self.debug.error("Could not normalize white space:\n %s", e)
            return df

    def format(
        self,
        df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Universally format cell values to strings for data comparison.
        Returns an empty data frame if it fails.
        """
        output = pd.DataFrame()

        if df.empty:
            issue = ReportIssue(
                "Formatting the data frame.",
                "Attempted to format the given data frame, but the data frame was empty.",
                "error",
            )
            self.report_issues.append(issue)
            self.journal.error("Cannot format empty DataFrame. Formating stopped.")
            return pd.DataFrame()

        try:
            index_keys = self.metadata.get_table_index_keys()

            # Remove blank columns if they exist
            df = self._drop_na_columns(df)

            df = self._normalize_key_columns(df, index_keys)

            # Remove blank rows if they exist
            df = self._drop_na_rows(df, index_keys)

            # Format datetimes to a merck standard string
            df = self._conform_datetime_columns(df)

            # Format numerical columns cell-be-cell.
            df = self._conform_numeric_columns(df)

            # Conform blank cells to pd.NA
            df = self._conform_blank_cells(df, index_keys)

            # Replace to standardize bools and blanks to python types
            normal_cols = [col for col in df.columns if col not in index_keys]
            df[normal_cols] = df[normal_cols].replace(_VALUE_NORMALIZATION_MAP)

            output = self._normalize_whitespace(df)
            output = self._normalize_key_columns(output, index_keys)
            output = output.astype("string")
            return output

        except Exception as e:
            error_msg = f"Could not format dataframe:\n{e}"
            self.journal.error(error_msg)
            self.debug.error("An unexpected error occurred during formating:\n %s", e)
            issue = ReportIssue(
                "Unexpected Format Error",
                "An unexpected error occurred during formatting.",
                "critical",
            )
            self.report_issues.append(issue)
            return output

    def could_format(
        self, mtl_dataframe: pd.DataFrame, input_dataframe: pd.DataFrame
    ) -> bool:
        """
        Checks data frames and returns a bool if they could be formatted.
        """
        if mtl_dataframe.empty:
            self.journal.error_banner("MTL data formatting failed.")
            return False
        if input_dataframe.empty:
            self.journal.error_banner("Input data formatting failed.")
            return False
        self.journal.info("MTL formatted successfully!")
        self.journal.info("MTL shape after formatting:")
        self.journal.info(f"       Rows: {mtl_dataframe.shape[0]}")
        self.journal.info(f"    Columns: {mtl_dataframe.shape[1]}")
        self.journal.info("Input formatted successfully!")
        self.journal.info("Input shape after formatting:")
        self.journal.info(f"       Rows: {input_dataframe.shape[0]}")
        self.journal.info(f"    Columns: {input_dataframe.shape[1]}")
        return True

    def _classic_data_check(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Helper function that checks the table type and determines whether
        to add classic columns to the table if not already present.
        """
        _df = df.copy()
        table_type = self.metadata.table_type
        formatting = self.metadata.dataframe_formatting["classic_gxp_columns"]
        classic_columns = set(formatting)

        if table_type == TableType.GXP:
            if classic_columns.issubset(set(_df.columns)):
                self.journal.info("Classic columns found.")
                return _df
            else:
                for col in classic_columns:
                    if col not in _df.columns:
                        _df[col] = None
                self.journal.info("Classic columns applied.")
        return _df

    def conform_columns(
        self,
        mtl_df: pd.DataFrame,
        input_df: pd.DataFrame,
        use_version: bool = False,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        A function that attempts to conform the input data frame columns to match the
        MTL data frame columns for comparison.
        Returns empty data frames if it fails.
        """

        if mtl_df.empty or input_df.empty:
            issue = ReportIssue(
                "Empty data frame check",
                "While conforming columns one or both of the supplied data frames "
                "were empty.",
                "error",
            )
            self.report_issues.append(issue)
            self.journal.error("There was a problem conforming the columns.")
            self.journal.error("Cannot conform empty data frames.")
            return pd.DataFrame(), pd.DataFrame()

        _mtl = mtl_df.copy()
        _input = input_df.copy()
        output = (pd.DataFrame(), pd.DataFrame())

        try:
            if use_version:
                if "Version" not in _input.columns:
                    _input["Version"] = float(self.metadata.get_mtl_version()) + float(
                        1
                    )
            else:
                _input = _input.drop(columns=["Version"], errors="ignore")
                _mtl = _mtl.drop(columns=["Version"], errors="ignore")

            mtl_cols = _mtl.shape[1]
            input_cols = _input.shape[1]

            self.journal.info("Checking input for classic MTL columns.")
            _input = self._classic_data_check(_input)

            if mtl_cols != input_cols or (_mtl.dtypes != _input.dtypes).any():
                self.journal.warning("Columns do not align!")
                self.journal.warning(
                    "Columns or types may not be aligned and will now be tested and changed."
                )
                report_shape_differences(self.reporter, mtl_df, input_df)
            else:
                self.journal.info("Columns are aligned correctly. Continuing...")
                output = (_mtl, _input)
                return output

            # Ensure df data is using the same columns as the mtl
            # by filtering the df columns by the mtl columns
            column_difference = set(_input.columns) ^ set(_mtl.columns)
            if column_difference:
                self.journal.warning("The current difference in columns are:")
                for i, col in enumerate(column_difference):
                    self.journal.warning(f"    {i}:{col}")

            self.journal.info("Aligning columns...")
            _input = _input[_mtl.columns]
            self.journal.info("✓ Input data columns have aligned to the MTL columns!")
            self.journal.info(f"✓ {len(_mtl.columns)} columns set.")
            self.journal.info("Columns used within this comparison:")

            for index, col in enumerate(_input.columns):
                self.journal.info(f"    {index}:{col}")

            # Ensure the column data types are the same by matching the input
            # dtypes to the mtl dtypes
            self.journal.info("Standardizing data types...")
            self.journal.info("Casting Input types to match the MTL columns.")

            for col in _input.columns:
                self.debug.debug("Casting '%s' column.", col)
                if col in _mtl.columns:
                    _input[col] = _input[col].astype(  # type: ignore
                        _mtl[col].dtype  # type: ignore
                    )
                    self.debug.debug(
                        "Input type: '%s' changed to MTL type: '%s'.",
                        _input[col].dtype,
                        _mtl[col].dtype,
                    )

            self.journal.info("Data types aligned!")

            output = (_mtl, _input)
            return output  # type: ignore

        except KeyError as e:
            error_msg = "Column mismatch: The input file is missing required columns."
            self.journal.error_banner(error_msg)
            self.journal.error(f"\n{e}\n")
            return output
        except Exception as e:
            msg = "Data alignment failed! An unexpected error occurred."
            self.journal.error(msg)
            self.debug.error(msg + ":\n %s", e)
            return output
