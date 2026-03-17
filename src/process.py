# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
#
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH

# stdlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

# third party
import pandas as pd
import openpyxl as xl
import ttkbootstrap as ttk

# local
from src.paths import CONFIG_PATH, REPORTS_DIR
from src.reporting import Reporting

logger = logging.getLogger(__name__)
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


class Process:
    """
    The theoretical process of this app is to pull the MTL excel file from mango,
    and pull the relevant data from PI builder into a CSV.
    The input csv data should be collected with all possible columns.
    This process will then filter down the csv columns to the matching MTL table
    columns.
    Then, the input data can either be compared against the MTL data,
    or the input data can be appended to the MTL for quick formatting and
    validation comparisons.
    To 'append' data, the input csv should include the full data pulled from
    PI Builder to keep the ultra specific sorting rules of the MTL.
    Appending will then compare the old data to the new and supply a list of
    found changes.
    """

    def __init__(
        self,
        report: Reporting,
    ) -> None:
        self.report = report
        # Pull external config
        self.worksheet_metadata = {
            sheet_name: TableInfo(
                table_id=entry["table_id"],
                type=TableType[entry["type"]],
                can_process=entry["can_process"],
            )
            for sheet_name, entry in _config["worksheet_metadata"].items()
        }
        self.table_formatting = {
            TableType[key]: {
                "Object Type Order": entry["object_type_order"],
                "Sort Order": entry["sort_order"],
                "Sort Direction": entry["sort_direction"],
            }
            for key, entry in _config["table_formatting"].items()
        }
        # dataframe_formatting holds lists like,
        #   "numeric_columns"
        #   "classic_gxp_columns"
        self.dataframe_formatting = _config["dataframe_formatting"]
        self.can_process_worksheets = {
            sheetname
            for sheetname, table in self.worksheet_metadata.items()
            if table.can_process
        }

    def _get_mtl_table(
        self,
        file_name: str,
        worksheet_name: str,
        table_id: str,
    ) -> pd.DataFrame | None:
        """
        Returns a data frame from a named excel table in the MTL, or None if it fails.
        """
        try:
            workbook = xl.load_workbook(file_name, data_only=True)
            self.report.info("Loaded workbook.")
            self.report.info(
                f"Extracting excel table {table_id} from worksheet {worksheet_name}..."
            )
            worksheet = workbook[worksheet_name]
            # return the cell range of the named table
            data_range = worksheet.tables[table_id].ref
            self.report.info("Loaded table.")
            # return a 2d array of table data
            table = [[cell.value for cell in row] for row in worksheet[data_range]]  # type: ignore
            # get header and row data
            headers = table[0]
            rows = table[1:]
            self.report.info("Retrieved table data!")
            # create the data frame
            dataframe = pd.DataFrame(rows, columns=headers)  # type: ignore
            self.report.info("Data frame created.")
            return dataframe
        except Exception as e:
            error_msg = f"Could not extract excel table into a data frame:\n{e}"
            self.report.exception(error_msg, popup=True)
            return None
        finally:
            if "workbook" in dir():
                workbook.close()
                self.report.info("Workbook closed.")

    def _get_input_table(
        self,
        file_path: str,
        filter: str,
    ) -> pd.DataFrame | None:
        """
        Returns a data frame from an input csv file, or None if it fails.
        """
        # Read the input csv
        try:
            df = pd.read_csv(
                file_path,
                na_values=["None", "none", "NULL", "null", ""],
                keep_default_na=True,
                encoding="utf-8",
            )
            return df
        except Exception as e:
            self.report.warning("Could not read supplied CSV file!")
            self.report.exception(f"\n{e}")
            self.report.warning("Will attempt to convert known problem symbols...")
            try:
                df = pd.read_csv(
                    file_path,
                    na_values=["None", "none", "NULL", "null", ""],
                    keep_default_na=True,
                    encoding="latin-1",
                )
                df = df.replace("�C", "°C", regex=False)
                df = df.replace("�F", "°F", regex=False)
                fixed_name = f"{filter}_fixed.csv"
                fixed_file = self.report.report_folder / fixed_name
                df.to_csv(fixed_file, encoding="utf-8-sig")
                df = pd.read_csv(
                    fixed_file,
                    na_values=["None", "none", "NULL", "null", ""],
                    keep_default_na=True,
                )
                self.report.info("Conversion completed!")
                self.report.info(f"Converted input saved to: {fixed_name}")
                return df
            except Exception as e:
                error_msg = "Conversion attempt failed. Please report this error."
                self.report.critical(error_msg, popup=True)
                return None

    def _report_comparison(
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
            error_msg = f"Could not log comparison data:\n{e}"
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

    def _compare_shapes(
        self,
        df_1: pd.DataFrame,
        df_2: pd.DataFrame,
        df_1_name: str = "df_1",
        df_2_name: str = "df_2",
    ) -> dict | None:
        """
        Compare shapes of two data frames and return difference information.
        Returns a dictionary with shape comparison details or None if it fails.
        """
        shape_1 = df_1.shape
        shape_2 = df_2.shape
        comparison = {
            "shapes_equal": shape_1 == shape_2,
            f"{df_1_name}_shape": shape_1,
            f"{df_2_name}_shape": shape_2,
            "row_difference": shape_1[0] - shape_2[0],
            "column_difference": shape_1[1] - shape_2[1],
        }
        # Log the shape comparison
        self.report.subtitle("DATA FRAME SHAPE COMPARISON")
        self.report.info(f"{df_1_name} shape: {shape_1[0]} rows × {shape_1[1]} columns")
        self.report.info(f"{df_2_name} shape: {shape_2[0]} rows × {shape_2[1]} columns")
        # If either data frame shape is 0, fail the comparison.
        if shape_1[0] == 0 or shape_2[0] == 0:
            # Failed comparison
            return None
        # If the rows from each shape do not match...
        if shape_1[0] != shape_2[0]:
            # Find the number of different rows
            row_diff = abs(shape_1[0] - shape_2[0])
            # Report out the difference
            if shape_1[0] > shape_2[0]:
                self.report.warning(
                    f"{df_1_name} has {row_diff} MORE rows than {df_2_name}."
                )
            else:
                self.report.warning(
                    f"{df_2_name} has {row_diff} MORE rows than {df_1_name}."
                )
        else:
            self.report.info("Row counts match.")
        # If the columns from each shape do not match...
        if shape_1[1] != shape_2[1]:
            # Find the number of different columns
            col_diff = abs(shape_1[1] - shape_2[1])
            # Report out the difference
            if shape_1[1] > shape_2[1]:
                self.report.warning(
                    f"{df_1_name} has {col_diff} MORE columns than {df_2_name}."
                )
            else:
                self.report.warning(
                    f"{df_2_name} has {col_diff} MORE columns than {df_1_name}."
                )
        else:
            self.report.info("Column counts match.")
        return comparison

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

    def _format_dataframe(
        self, table_type: TableType, df: pd.DataFrame, name_filter: str | None = None
    ) -> pd.DataFrame | None:
        """
        Helper function that formats and sorts data frames for equality comparisons.
        Returns None if an error occurs.
        """
        name_filter = name_filter or None
        try:
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
            output = output.replace(
                {
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
            )
            # Change everything to strings for faster comparisons
            output = output.astype("string")
            output = self._normalize_whitespace(output)
            return output
        except Exception as e:
            error_msg = f"Could not format dataframe:\n{e}"
            self.report.exception(error_msg, popup=True)
            return None

    def compare_datasets(
        self,
        name_filter: str,
        input_file: str,
        mtl_file: str,
        mtl_worksheet_name: str,
    ) -> bool | None:
        """
        Compare the supplied PI builder data and the MTL/CMD.
        Returns None if process fails.
        """
        self.report.title(f"COMPARISON STARTED FOR: {name_filter or 'None'}")

        # Check if the table can be processed.
        if not self.worksheet_metadata[mtl_worksheet_name].can_process:
            self.report.highlight_titled_error(
                "✗ This table does not yet have the capability to process data.",
            )
            self.report.save_report()
            return None

        mtl_table_id = self.worksheet_metadata[mtl_worksheet_name].table_id
        worksheet_type = self.worksheet_metadata[mtl_worksheet_name].type

        self.report.debug(f"Selected worksheet: {mtl_worksheet_name}")
        self.report.debug(f"Table type: {worksheet_type.name}")
        self.report.debug(f"Filtering data with string: {name_filter or 'None'}")

        self.report.title("Phase 1: Extracting data sources.")

        # Extract the mtl table
        self.report.info("Extracting MTL table...")
        mtl_dataframe = self._get_mtl_table(mtl_file, mtl_worksheet_name, mtl_table_id)
        if mtl_dataframe is None:
            self.report.highlight_titled_error("✗ MTL data could not be extracted.")
            self.report.save_report()
            return None
        self.report.info(
            f"✓ MTL extracted successfully with {mtl_dataframe.shape[0]} rows and {mtl_dataframe.shape[1]} columns."
        )

        # Extract the input csv
        self.report.info("Extracting the input CSV...")
        input_dataframe = self._get_input_table(input_file, name_filter)
        if input_dataframe is None:
            self.report.highlight_titled_error("✗ Input CSV could not be extracted.")
            self.report.save_report()
            return None
        self.report.info(
            f"✓ Input CSV extracted successfully with {input_dataframe.shape[0]} rows and {input_dataframe.shape[1]} columns."
        )

        self.report.title("Phase 2: Formatting and preparing data for comparison.")

        # Drop the version column, input data will not have it
        mtl_dataframe = mtl_dataframe.drop(columns=["Version"], errors="ignore")

        # Sort and format the mtl data
        self.report.info("Formatting MTL dataframe...")
        mtl_dataframe = self._format_dataframe(
            worksheet_type, mtl_dataframe, name_filter
        )
        if mtl_dataframe is None:
            self.report.highlight_titled_error("✗ MTL data formatting failed.")
            self.report.save_report()
            return None
        self.report.info("✓ MTL formatted successfully!")
        self.report.info("✓ MTL shape after formatting:")
        self.report.info(f"✓        Rows: {mtl_dataframe.shape[0]}")
        self.report.info(f"✓     Columns: {mtl_dataframe.shape[1]}")

        # Sort and format the input data
        self.report.info("Formatting Input dataframe...")
        input_dataframe = self._format_dataframe(
            worksheet_type, input_dataframe, name_filter
        )
        if input_dataframe is None:
            self.report.highlight_titled_error(
                "✗ Could not format the Input data frame."
            )
            self.report.save_report()
            return None
        self.report.info("✓ Input CSV formatted successfully!")
        self.report.info("✓ Input CSV shape after formatting:")
        self.report.info(f"✓         Rows: {input_dataframe.shape[0]}")
        self.report.info(f"✓      Columns: {input_dataframe.shape[1]}")

        self.report.title("Phase 3: Conforming input columns to MTL standard.")

        try:
            # Ensure input data is using the same columns as the mtl
            # by filtering the input columns by the mtl columns
            self.report.info("Aligning columns...")
            input_dataframe = input_dataframe[mtl_dataframe.columns]
            self.report.info("✓ Columns aligned to MTL formatting!")
            self.report.info(f"✓ {len(mtl_dataframe.columns)} columns set.")

            # Ensure the column data types are the same by changing all
            # dtypes to string
            self.report.info("Standardizing data types...")
            for col in input_dataframe.columns:
                if col in mtl_dataframe.columns:
                    mtl_dataframe[col] = mtl_dataframe[col].astype(  # type: ignore
                        input_dataframe[col].dtype  # type: ignore
                    )
            self.report.info("✓ Data types aligned!")
        except KeyError as e:
            error_msg = (
                f"✗ Column mismatch: Input file is missing required columns.\n{e}"
            )
            self.report.highlight_titled_error(error_msg)
            self.report.error(error_msg)
            self.report.save_report()
            return None
        except Exception as e:
            self.report.highlight_titled_error(f"✗ Data alignment failed:\n{e}")
            self.report.save_report()
            return None

        self.report.title("Phase 4: Running validation checks.")

        try:
            # Compare DF Shapes
            shape_comparison = self._compare_shapes(
                mtl_dataframe, input_dataframe, "MTL", "Input"  # type: ignore
            )
            if shape_comparison is None:
                self.report.error(
                    "✗ No data was comparable. Check your object filter or supplied files.",
                    popup=True,
                )
                self.report.highlight_titled_error(
                    "✗ Shape comparison detected empty data frames."
                )
                self.report.save_report()
                return None

            # Find missing rows if shapes differ
            if not shape_comparison["shapes_equal"]:
                self.report.warning(
                    "✗ Shape mismatch detected - checking for missing rows..."
                )
                self._find_missing_rows(
                    mtl_dataframe, input_dataframe, "MTL", "Input", key_column="Name"  # type: ignore
                )

            self.report.info("Running detailed data frame comparison...")
            self._report_comparison(mtl_dataframe, input_dataframe, "MTL", "Input")  # type: ignore

            self.report.title("PROCESS COMPLETE")
            self.report.info("All validation checks completed.")
            self.report.info(
                "Review the generated .LOG and CSV files for detailed results."
            )
            self.report.save_report()
            return True

        except Exception as e:
            self.report.highlight_titled_error("Validation process failed!")
            self.report.critical(
                f"Unexpected error during validation:\n{e}", popup=True
            )
            self.report.save_report()
            return None

    def append(self) -> None:
        """
        Add or append new data to the MTL/CMD file.
        """
        raise NotImplementedError("append() has not yet been implemented.")


if __name__ == "__main__":
    FORMAT = "%(asctime)s:%(levelname)s:%(filename)s:%(name)s::%(message)s"
    logging.basicConfig(
        filename="debug_process.log",
        filemode="w",
        format=FORMAT,
        encoding="utf-8",
        level=logging.DEBUG,
    )
    window = ttk.Window()
    report = Reporting(window, REPORTS_DIR)
    report.create_report("debug")
    process = Process(report)
    process.report.error("This module should not be run as a script.")
    exit()
