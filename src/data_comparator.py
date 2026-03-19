# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
#
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH

# stdlib

# third party
import pandas as pd

# local
from src.metadata import WORKSHEET_METADATA
from src.reporting import Reporting


class DataComparator:
    def __init__(self, report: Reporting) -> None:
        self.report = report
        self.ws_metadata = WORKSHEET_METADATA

    def _report_missing_rows(
        self,
        mtl_dataframe: pd.DataFrame,
        input_dataframe: pd.DataFrame,
        key_column: str = "Name",
    ) -> None:
        """
        Find rows that exist in one data frame but not the other.
        """
        mtl_df = mtl_dataframe.copy()
        input_df = input_dataframe.copy()

        try:
            # Get unique identifiers from both data frames
            mtl_keys = set(mtl_df[key_column].dropna().unique())
            input_keys = set(input_df[key_column].dropna().unique())
            # Find differences
            mtl_only_keys = mtl_keys - input_keys
            input_only_keys = input_keys - mtl_keys
            # Get the actual rows
            mtl_only_rows = mtl_df[mtl_df[key_column].isin(mtl_only_keys)]  # type: ignore
            input_only_rows = input_df[input_df[key_column].isin(input_only_keys)]  # type: ignore
            # Log findings
            self.report.subtitle("Reporting row differences.")
            self.report.error(f"Row differences based on '{key_column}' column.")
            self.report.error("Review the following inconsistencies.")
            # If df_1 has keys not in df_2
            if len(mtl_only_keys) > 0:
                self.report.subtitle(
                    f"Found {len(mtl_only_rows)} rows ONLY in the MTL:"
                )
                # Iterate through the data frame rows
                for index, row in mtl_only_rows.iterrows():
                    self.report.error(f"Row {index}:")
                    for col in mtl_only_rows.columns:
                        self.report.error(f"  {col}: {row[col]}")
                    self.report.error(f"{'-'*40}")
                df_1_rows_filename = "rows_only_within_MTL.csv"
                df_1_rows_filepath = self.report.report_folder / df_1_rows_filename
                mtl_only_rows.to_csv(df_1_rows_filepath, index=False)
                self.report.error(f"Exported to: {df_1_rows_filename}")
            else:
                self.report.info("No rows found exclusively in MTL")
            # If df_2 has keys not in df_1
            if len(input_only_keys) > 0:
                self.report.subtitle(
                    f"Found {len(input_only_rows)} rows ONLY in the Input:"
                )
                self.report.error(f"{'-'*80}")
                # Iterate through the data frame rows
                for index, row in input_only_rows.iterrows():
                    self.report.error(f"Row {index}:")
                    for col in input_only_rows.columns:
                        self.report.error(f"  {col}: {row[col]}")
                    self.report.error(f"{'-'*40}")
                df_2_rows_filename = "rows_only_within_input.csv"

                df_2_rows_filepath = self.report.report_folder / df_2_rows_filename
                input_only_rows.to_csv(df_2_rows_filepath, index=False)
                self.report.error(f"Exported to: {df_2_rows_filename}")
            else:
                self.report.info("No rows found exclusively in the Input csv.")
            # Log number of common rows
            common_keys = mtl_keys & input_keys
            self.report.info(f"{len(common_keys)} rows exist in BOTH dataframes")
        except Exception as e:
            error_msg = f"There was a problem returning the row comparison:\n{e}"
            self.report.exception(error_msg, popup=True)

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

    def compare_shapes(
        self,
        mtl_df: pd.DataFrame | None,
        input_df: pd.DataFrame | None,
    ) -> dict | None:
        """
        A General comparison of data frame shape.
        Returns a dictionary with shape comparison details or None if it fails.
        """
        if mtl_df is None or input_df is None:
            self.report.error("Cannot compare empty data frames.")
            self.report.error("Stopping comparison process.")
            return None

        try:

            mtl_shape = mtl_df.shape
            input_shape = input_df.shape
            mtl_rows = mtl_shape[0]
            mtl_cols = mtl_shape[1]
            input_rows = input_shape[0]
            input_cols = input_shape[1]
            comparison = {
                "shapes_equal": mtl_shape == input_shape,
                "mtl_shape": mtl_shape,
                "input_shape": input_shape,
                "row_difference": mtl_rows - input_rows,
                "column_difference": mtl_cols - input_cols,
            }
            return comparison
        except Exception as e:
            error_msg = f"An unexpected error occurred!\n{e}"
            self.report.error(
                "Could not compare data frame shapes. Check logs.", popup=True
            )
            self.report.exception(error_msg)
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
            self.report.info("Aligning columns...")
            column_difference = set(_input.columns) ^ set(_mtl.columns)
            if column_difference:
                self.report.warning("The current difference in columns are:")
                for i, col in enumerate(column_difference):
                    self.report.warning(f"    {i}:{col}")
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
                self.report.debug(f"Casting {col} column.")
                if col in _mtl.columns:
                    self.report.debug(
                        f"Input type: {_input[col].dtype} changed to MTL type: {_mtl[col].dtype}."
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
            self.report.save_report()
            return None
        except Exception as e:
            self.report.highlight_titled_error("Data alignment failed!")
            self.report.error(f"\n{e}")
            self.report.save_report()
            return None

    def _report_row_differences(
        self, mtl_dataframe: pd.DataFrame, input_dataframe: pd.DataFrame, comparison
    ):
        """
        Reports specific row differences
        """
        mtl_df = mtl_dataframe.copy()
        input_df = input_dataframe.copy()
        row_diff = comparison

        self.report.highlight_error("Row difference found!")
        self.report.error(f"Found differences in {len(row_diff)} rows!:")
        self.report.subtitle("DETAILING ROW DIFFERENCES:")
        # Iterate through each row that has differences
        for row_idx in row_diff.index:
            self.report.error(f"{'-'*60}")
            self.report.error(f"Row: {row_idx}")
            # Get the actual row data from both dataframes for context
            # Check if the index exists in both (it should for compared rows)
            if row_idx in mtl_df.index and row_idx in input_df.index:
                # Show identifying information (e.g., Name column)
                if "Name" in mtl_df.columns:
                    name_val = mtl_df.loc[row_idx, "Name"]
                    self.report.error(f"  Name: {name_val}")
                    self.report.error(f"{'─'*30}")
            # Iterate through columns that have differences
            for col in row_diff.columns.levels[0]:  # type: ignore
                # Check if this column has a difference for this row
                if (col, "MTL") in row_diff.columns and (
                    col,
                    "Input",
                ) in row_diff.columns:
                    val_1 = row_diff.loc[row_idx, (col, "MTL")]
                    val_2 = row_diff.loc[row_idx, (col, "Input")]
                    # Only report if at least one value is not null/blank
                    if pd.notna(val_1) or pd.notna(val_2):
                        # Handle None/NaN display
                        display_val_1 = val_1 if pd.notna(val_1) else "<No Data>"
                        display_val_2 = val_2 if pd.notna(val_2) else "<No Data>"
                        self.report.error(f"    Column: {col}")
                        self.report.error(f"           MTL: {display_val_1}")
                        self.report.error(f"         Input: {display_val_2}")
                        self.report.error(f"{'─'*30}")
        self.report.error(f"{'='*80}")
        comparison_filename = f"{self.report.cleaned_name}_comparison.csv"
        comparison_filepath = self.report.report_folder / comparison_filename
        errored_filename_df1 = "mtl_bad_comparison.csv"
        errored_filename_df2 = "input_bad_comparison.csv"
        errored_filepath_df1 = self.report.report_folder / errored_filename_df1
        errored_filepath_df2 = self.report.report_folder / errored_filename_df2
        row_diff.to_csv(comparison_filepath, index=True)
        self.report.info(f"Comparison table saved to: {comparison_filename}")
        mtl_df.to_csv(errored_filepath_df1, index=True)
        self.report.info(f"MTL table saved to: {errored_filename_df1}")
        input_df.to_csv(errored_filepath_df2, index=True)
        self.report.info(f"Input table saved to: {errored_filename_df2}")

        return mtl_df, input_df

    def compare_rows(
        self, mtl_dataframe: pd.DataFrame | None, input_dataframe: pd.DataFrame | None
    ):
        """
        Reports a detailed comparison of row differences. Returns None if it fails.
        """

        # If data frame shapes do not match fail the comparison
        if mtl_dataframe is None or input_dataframe is None:
            self.report.error("Cannot compare empty data frames.", popup=True)
            return None

        # TODO: 001 - Implement a comparison key for each table, and pull mtl_ws_name
        # key_column = WORKSHEET_METADATA[mtl_worksheet_name].comparison_key

        mtl_df = mtl_dataframe.copy()
        input_df = input_dataframe.copy()
        mtl_rows = mtl_dataframe.shape[0]
        input_rows = input_dataframe.shape[0]

        try:
            # If rows are empty fail the comparison
            if mtl_rows == 0 or input_rows == 0:
                self.report.highlight_titled_error(
                    "✗ Shape comparison detected empty data frames rows."
                )
                self.report.error("✗ Cannot compare data frames without row data.")
                self.report.error(
                    "✗ Check your object filter or supplied files.", popup=True
                )
                return None

            # If rows differ, report difference
            if mtl_rows != input_rows:
                min_rows = min(mtl_rows, input_rows)
                self.report.highlight_error("Data frame rows do not align!")
                self._report_shape_differences(mtl_rows, input_rows, "ROW")
                self.report.error("✗ Row counts differ!")
                self.report.error("✗ Cannot make a full comparison.")
                self.report.error("✗ Will now attempt to report the erroneous rows.")
                self.report.error("✗ Due to comparison limitations...")
                self.report.error(f"✗ Can only compare the first {min_rows} rows,")
                self.report.error(
                    f"✗ Errors after row {min_rows} must be manually compared."
                )

                row_comparison = mtl_df.iloc[:min_rows].compare(
                    input_df.iloc[:min_rows],
                    align_axis=1,
                    result_names=("MTL", "Input"),
                )

                # TODO: implement better column key logic see above # TODO: 001
                self._report_missing_rows(mtl_df, input_df, "Name")
            else:
                self.report.info("Rows compared successfully!")
                row_comparison = mtl_df.compare(
                    input_df, align_axis=1, result_names=("MTL", "Input")
                )

            if row_comparison.empty:
                self.report.info("No differences found in common rows!")
                self.report.info("Comparison of the MTL to the Input CSV is sound!")
                self.report.info(
                    "See these reported table files for the detailed breakdown:"
                )
                mtl_report_name = "mtl_good_comparison.csv"
                input_report_name = "input_good_comparison.csv"
                mtl_report_file = self.report.report_folder / mtl_report_name
                input_report_file = self.report.report_folder / input_report_name
                self.report.info(f"MTL comparison proof saved to: {mtl_report_file}")
                self.report.info(
                    f"Input comparison proof saved to: {input_report_file}"
                )
                mtl_df.to_csv(mtl_report_file, index=True)
                input_df.to_csv(input_report_file, index=True)
            else:
                self._report_row_differences(mtl_df, input_df, row_comparison)
                return True
        except Exception as e:
            error_msg = f"Unexpected error during reporting:\n{e}"
            self.report.exception(error_msg, popup=True)
