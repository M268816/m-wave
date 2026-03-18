# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
#
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH

# stdlib

# third party
import pandas as pd

# local
from src.data_extraction import DataExtractor
from src.data_formatter import DataFormatter
from src.metadata import WORKSHEET_METADATA
from src.reporting import Reporting


class DataComparator:
    def __init__(self, report: Reporting) -> None:
        self.report = report
        self.ws_metadata = WORKSHEET_METADATA
        self.data_extractor = DataExtractor(self.report)
        self.data_formatter = DataFormatter(self.report)

    def comparison_report(
        self,
        df_1: pd.DataFrame,
        df_2: pd.DataFrame,
        df_1_name: str = "df_1",
        df_2_name: str = "df_2",
    ) -> None:
        """
        Logs and reports the differences in the supplied data frames.
        """
        self.report.subtitle(f"COMPARISON REPORT FOR: {df_1_name} vs {df_2_name}")
        try:
            # Initial equality check
            data_is_equal = df_1.equals(df_2)
            if data_is_equal:
                self.report.info("The supplied data structures are Equal!")
            else:
                self.report.highlight_titled_error(
                    "The supplied data structures are not equal."
                )
            self.report.info("Comparing data frame shapes...")
            # If data frame shapes do not match
            if df_1.shape != df_2.shape:
                self.report.highlight_error("DATA FRAME SHAPE ERROR")
                # Only compare common rows if row counts differ
                if df_1.shape[0] != df_2.shape[0]:
                    min_rows = min(df_1.shape[0], df_2.shape[0])
                    self.report.error("Row counts differ!")
                    self.report.error("Cannot make a full comparison.")
                    self.report.error(f"Comparing first {min_rows} rows only...")
                    row_diff = df_1.iloc[:min_rows].compare(
                        df_2.iloc[:min_rows],
                        align_axis=1,
                        result_names=(df_1_name, df_2_name),
                    )
                else:
                    self.report.info("Row counts the same!")
                    row_diff = df_1.compare(
                        df_2, align_axis=1, result_names=(df_1_name, df_2_name)
                    )
            else:
                self.report.info("Data frame shapes are equal!")
                row_diff = df_1.compare(
                    df_2, align_axis=1, result_names=(df_1_name, df_2_name)
                )

            if row_diff.empty:
                self.report.info("No differences found in common rows!")
                self.report.info(f"Comparison of {df_1_name} to {df_2_name} is sound!")
                self.report.info(
                    "See these reported table files for the detailed breakdown:"
                )
                df_1_report_name = f"{df_1_name}_good_comparison.csv"
                df_2_report_name = f"{df_2_name}_good_comparison.csv"
                df_1_report_file = self.report.report_folder / df_1_report_name
                df_2_report_file = self.report.report_folder / df_2_report_name
                self.report.info(
                    f"{df_1_name} comparison proof saved to: {df_1_report_file}"
                )
                self.report.info(
                    f"{df_2_name} comparison proof saved to: {df_2_report_file}"
                )
                df_1.to_csv(df_1_report_file, index=True)
                df_2.to_csv(df_2_report_file, index=True)
            else:
                self.report.highlight_error("Row difference found!")
                self.report.error(f"Found differences in {len(row_diff)} rows!:")
                self.report.subtitle("DETAILED DIFFERENCES:")
                # Iterate through each row that has differences
                for row_idx in row_diff.index:
                    self.report.error(f"{'-'*60}")
                    self.report.error(f"Row: {row_idx}")
                    # Get the actual row data from both dataframes for context
                    # Check if the index exists in both (it should for compared rows)
                    if row_idx in df_1.index and row_idx in df_2.index:
                        # Show identifying information (e.g., Name column)
                        if "Name" in df_1.columns:
                            name_val = df_1.loc[row_idx, "Name"]
                            self.report.error(f"  Name: {name_val}")
                    # Iterate through columns that have differences
                    for col in row_diff.columns.levels[0]:  # type: ignore
                        # Check if this column has a difference for this row
                        if (col, df_1_name) in row_diff.columns and (
                            col,
                            df_2_name,
                        ) in row_diff.columns:
                            val_1 = row_diff.loc[row_idx, (col, df_1_name)]
                            val_2 = row_diff.loc[row_idx, (col, df_2_name)]
                            # Only report if at least one value is not null/blank
                            if pd.notna(val_1) or pd.notna(val_2):
                                # Handle None/NaN display
                                display_val_1 = (
                                    val_1 if pd.notna(val_1) else "<No Data>"
                                )
                                display_val_2 = (
                                    val_2 if pd.notna(val_2) else "<No Data>"
                                )
                                self.report.error(f"  Column: {col}")
                                self.report.error(f"    {df_1_name}: {display_val_1}")
                                self.report.error(f"    {df_2_name}: {display_val_2}")
                self.report.error(f"{'='*80}")
                comparison_filename = f"{self.report.cleaned_name}_comparison.csv"
                comparison_filepath = self.report.report_folder / comparison_filename
                errored_filename_df1 = f"{df_1_name}_bad_comparison.csv"
                errored_filename_df2 = f"{df_2_name}_bad_comparison.csv"
                errored_filepath_df1 = self.report.report_folder / errored_filename_df1
                errored_filepath_df2 = self.report.report_folder / errored_filename_df2
                row_diff.to_csv(comparison_filepath, index=True)
                self.report.info(f"Comparison table saved to: {comparison_filename}")
                df_1.to_csv(errored_filepath_df1, index=True)
                self.report.info(f"{df_1_name} table saved to: {errored_filename_df1}")
                df_2.to_csv(errored_filepath_df2, index=True)
                self.report.info(f"{df_2_name} table saved to: {errored_filename_df2}")
        except Exception as e:
            error_msg = f"Unexpected error during reporting:\n{e}"
            self.report.exception(error_msg, popup=True)

    def _find_missing_rows(
        self,
        df_1: pd.DataFrame,
        df_2: pd.DataFrame,
        df_1_name: str = "df_1",
        df_2_name: str = "df_2",
        key_column: str = "Name",
    ) -> tuple[pd.DataFrame, pd.DataFrame] | None:
        """
        Find rows that exist in one data frame but not the other.
        Returns (rows_only_in_df_1, rows_only_in_df_2) or None if errored.
        """
        try:
            # Get unique identifiers from both data frames
            df_1_keys = set(df_1[key_column].dropna().unique())
            df_2_keys = set(df_2[key_column].dropna().unique())
            # Find differences
            df_1_only_keys = df_1_keys - df_2_keys
            df_2_only_keys = df_2_keys - df_1_keys
            # Get the actual rows
            df_1_only_rows = df_1[df_1[key_column].isin(df_1_only_keys)]  # type: ignore
            df_2_only_rows = df_2[df_2[key_column].isin(df_2_only_keys)]  # type: ignore
            # Log findings
            self.report.subtitle("Reporting row differences.")
            self.report.error(f"Row differences based on '{key_column}' column.")
            self.report.error("Review the following inconsistencies.")
            # If df_1 has keys not in df_2
            if len(df_1_only_keys) > 0:
                self.report.subtitle(
                    f"Found {len(df_1_only_rows)} rows ONLY in {df_1_name}:"
                )
                # Iterate through the data frame rows
                for index, row in df_1_only_rows.iterrows():
                    self.report.error(f"Row {index}:")
                    for col in df_1_only_rows.columns:
                        self.report.error(f"  {col}: {row[col]}")
                    self.report.error(f"{'-'*40}")
                df_1_rows_filename = f"rows_only_within_{df_1_name}.csv"
                df_1_rows_filepath = self.report.report_folder / df_1_rows_filename
                df_1_only_rows.to_csv(df_1_rows_filepath, index=False)
                self.report.error(f"Exported to: {df_1_rows_filename}")
            else:
                self.report.info(f"No rows found exclusively in {df_1_name}")
            # If df_2 has keys not in df_1
            if len(df_2_only_keys) > 0:
                self.report.subtitle(
                    f"Found {len(df_2_only_rows)} rows ONLY in {df_2_name}:"
                )
                self.report.error(f"{'-'*80}")
                # Iterate through the data frame rows
                for index, row in df_2_only_rows.iterrows():
                    self.report.error(f"Row {index}:")
                    for col in df_2_only_rows.columns:
                        self.report.error(f"  {col}: {row[col]}")
                    self.report.error(f"{'-'*40}")
                df_2_rows_filename = f"rows_only_within_{df_2_name}.csv"

                df_2_rows_filepath = self.report.report_folder / df_2_rows_filename
                df_2_only_rows.to_csv(df_2_rows_filepath, index=False)
                self.report.error(f"Exported to: {df_2_rows_filename}")
            else:
                self.report.info(f"No rows found exclusively in {df_2_name}")
            # Log number of common rows
            common_keys = df_1_keys & df_2_keys
            self.report.info(f"{len(common_keys)} rows exist in BOTH dataframes")
            return df_1_only_rows, df_2_only_rows  # type: ignore
        except Exception as e:
            error_msg = f"There was a problem returning the row comparison:\n{e}"
            self.report.exception(error_msg, popup=True)
            return None

    def _report_shape_differences(
        self, shape_1, shape_2, name_1, name_2, dimension
    ) -> bool:
        """
        Reports row or column count differences between two data frames.
        """
        dimension_plural = f"{dimension}s"

        if shape_1 == shape_2:
            self.report.info(f"✓ {dimension} counts match!")
        else:
            diff = abs(shape_1 - shape_2)
            larger, smaller = (
                (name_1, name_2) if shape_1 > shape_2 else (name_2, name_1)
            )
            self.report.warning(
                f"{larger} has {diff} more {dimension_plural} than {smaller}"
            )

        return False

    def compare_shapes(
        self,
        mtl: pd.DataFrame,
        input: pd.DataFrame,
        df_1_name: str = "df_1",
        df_2_name: str = "df_2",
    ) -> dict | None:
        """
        Compare shapes of two data frames and return difference information.
        Returns a dictionary with shape comparison details or None if it fails.
        """
        mtl_df = mtl.copy()
        input_df = input.copy()
        shape_1 = mtl.shape
        shape_2 = input.shape
        shape_1_rows = shape_1[0]
        shape_1_cols = shape_1[1]
        shape_2_rows = shape_2[0]
        shape_2_cols = shape_2[0]
        comparison = {
            "shapes_equal": shape_1 == shape_2,
            f"{df_1_name}_shape": shape_1,
            f"{df_2_name}_shape": shape_2,
            "row_difference": shape_1_rows - shape_2_rows,
            "column_difference": shape_1_cols - shape_2_cols,
        }

        # Log the shape comparison
        self.report.subtitle("DATA FRAME SHAPE COMPARISON")
        self.report.info(
            f"{df_1_name} shape: {shape_1_rows} rows × {shape_1_cols} columns"
        )
        self.report.info(
            f"{df_2_name} shape: {shape_2_rows} rows × {shape_2_cols} columns"
        )

        # If either shape is has empty rows fail the comparison
        if shape_1_rows == 0 or shape_2_rows == 0:
            self.report.highlight_titled_error(
                "✗ Shape comparison detected empty data frames rows."
            )
            self.report.error("✗ Cannot compare data frames without row data.")
            self.report.error(
                "✗ Check your object filter or supplied files.", popup=True
            )
            return None

        if not comparison["shapes_equal"]:
            self.report.warning("✗ Shape mismatch detected - checking rows...")
            self._report_shape_differences(
                shape_1_rows, shape_2_rows, df_1_name, df_2_name, "ROW"
            )
            self.report.warning("✗ Shape mismatch detected - checking columns...")
            self._report_shape_differences(
                shape_1_cols, shape_2_cols, df_1_name, df_2_name, "COLUMN"
            )
            self.report.warning(
                "✗ Shape mismatch detected - checking for missing rows..."
            )
            self._find_missing_rows(mtl_df, input_df, "MTL", "Input", key_column="Name")

        return comparison

    def could_format(
        self, mtl_dataframe: pd.DataFrame | None, input_dataframe: pd.DataFrame | None
    ) -> bool:
        if mtl_dataframe is None:
            self.report.highlight_titled_error("✗ MTL data formatting failed.")
            return False
        if input_dataframe is None:
            self.report.highlight_titled_error("✗ MTL data formatting failed.")
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

    def could_extract(
        self, mtl_dataframe: pd.DataFrame | None, input_dataframe: pd.DataFrame | None
    ) -> bool:
        if mtl_dataframe is None:
            self.report.highlight_titled_error("✗ MTL data could not be extracted.")
            return False
        if input_dataframe is None:
            self.report.highlight_titled_error("✗ Input CSV could not be extracted.")
            return False
        self.report.info("✓ MTL extracted successfully!")
        mtl_row_count = mtl_dataframe.shape[0]
        mtl_col_count = mtl_dataframe.shape[1]
        self.report.info(
            f"✓ The MTL has {mtl_row_count} rows and {mtl_col_count} columns."
        )
        self.report.info("✓ Input csv extracted successfully!")
        input_row_count = input_dataframe.shape[0]
        input_col_count = input_dataframe.shape[1]
        self.report.info(
            f"✓ The Input csv has {input_row_count} rows and {input_col_count} columns."
        )
        return True

    def can_process(self, worksheet_name: str) -> bool:
        """
        Check a MTL worksheet by name and determine if it can be processed.
        """
        if not self.ws_metadata[worksheet_name].can_process:
            self.report.highlight_titled_error(
                "✗ This table does not yet have the capability to process data.",
            )
            self.report.save_report()
            return False
        return True
