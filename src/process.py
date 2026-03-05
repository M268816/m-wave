import logging
import pandas as pd
import openpyxl as xl
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from src.reporting import Reporting
from tkinter.filedialog import askopenfilename as open_file

logger = logging.getLogger(__name__)


class TableType(int, Enum):
    UNKNOWN = 0
    ANALYTICS = 1
    GXP = 2
    ENUM_SET = 3
    CATEGORIES = 4
    TABLES = 5
    EVENT_FRAME = 6
    ELEMENT_TEMPLATE = 7
    ELEMENT = 8


@dataclass
class TableInfo:
    """
    A data class to hold the excel table name metadata.
    """

    table_id: str
    can_process: bool = False
    type: TableType = TableType.UNKNOWN


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

    def __init__(self, report_name: str = "generic_process_report") -> None:
        self.report_output_path = f"{datetime.now().isoformat()}_{report_name}"
        self.report = Reporting(report_name, output_dir=self.report_output_path)
        self.process_time = datetime.now().isoformat()
        self.worksheet_metadata = {
            "MTL-Analytics-VAL&PROD": TableInfo("Table5", type=TableType.ANALYTICS),
            "MTL GxP-VAL": TableInfo("Table2", type=TableType.GXP),
            "MTL GxP-PROD": TableInfo("Table3", type=TableType.GXP),
            "CMD-Enumeration Sets-VAL": TableInfo("Table6", type=TableType.ENUM_SET),
            "CMD-Enumeration Sets-PROD": TableInfo("Table7", type=TableType.ENUM_SET),
            "CMD Categories-VAL": TableInfo("Table8", type=TableType.CATEGORIES),
            "CMD Categories-PROD": TableInfo("Table9", type=TableType.CATEGORIES),
            "CMD Tables-VAL": TableInfo("Table10", type=TableType.TABLES),
            "CMD Tables-PROD": TableInfo("Table1012", type=TableType.TABLES),
            "CMD-Event Frame Templates-VAL": TableInfo(
                "Table14", True, type=TableType.EVENT_FRAME
            ),
            "CMD-Event Frame Templates-PROD": TableInfo(
                "Table1416", True, type=TableType.EVENT_FRAME
            ),
            "CMD-Element Templates-VAL": TableInfo(
                "Table12", True, type=TableType.ELEMENT_TEMPLATE
            ),
            "CMD-Element Templates-PROD": TableInfo(
                "Table13", True, type=TableType.ELEMENT_TEMPLATE
            ),
            "CMD-Elements-Build": TableInfo("Table11", type=TableType.ELEMENT),
        }
        self.can_process_worksheets = {
            sheetname
            for sheetname, table in self.worksheet_metadata.items()
            if table.can_process
        }

    def rename_report(self, new_name: str) -> None:
        """
        Renames the report.
        """
        self.report_output_path = f"{datetime.now().isoformat()}_{new_name}"
        self.report = Reporting(new_name, output_dir=self.report_output_path)

    def _get_excel_table(
        self,
        file_name: str,
        worksheet_name: str,
        table_id: str,
    ) -> pd.DataFrame:
        """
        Returns a data frame from a named excel table.
        """
        workbook = xl.load_workbook(file_name, data_only=True)
        try:
            self.report.info(
                f"Extracting excel table {table_id} from worksheet {worksheet_name}..."
            )
            self.report.info("Loaded workbook.")
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
            self.report.info("Workbook closed.")
            return dataframe
        except Exception as e:
            self.report.exception(
                f"Could not extract excel table into a data frame:\n{e}"
            )
            return pd.DataFrame()
        finally:
            workbook.close()

    def _report_comparison(
        self,
        df_1: pd.DataFrame,
        df_2: pd.DataFrame,
        df_1_name: str = "df_1",
        df_2_name: str = "df_2",
    ):
        """
        Logs and reports the differences in the supplied data frames.
        """
        try:
            self.report.info(f"{'='*80}")
            self.report.info(f"COMPARISON REPORT FOR: {df_1_name} vs {df_2_name}")
            self.report.info(f"{'='*80}")

            # Initial equality check
            data_is_equal = df_1.equals(df_2)
            if data_is_equal:
                self.report.info("The supplied data frame structures are Equal!")
            else:
                self.report.error(f"{'!'*80}")
                self.report.error("VALIDATION FAILED.")
                self.report.error("The supplied data structures are Not Equal!")
                self.report.error("See the following reports for the inconsistencies.")
                self.report.error(f"{'!'*80}")
            # If data frame shapes do not match
            self.report.info("Comparing data frame shapes.")
            if df_1.shape != df_2.shape:
                self.report.error(f"{'!'*80}")
                self.report.error("DATA FRAME SHAPE ERROR")
                self.report.error("Supplied dataframes have different shapes.")
                self.report.error("See the following comparison for more detail.")
                self.report.error(f"{'!'*80}")
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
                self.report.info(f"Validation of {df_1_name} to {df_2_name} is sound!")
                self.report.info(f"See these report files for detailed breakdown:")
                df_1_report_name = (
                    f"{self.report.file_name}_{df_1_name}_passing_validation.csv"
                )
                df_2_report_name = (
                    f"{self.report.file_name}_{df_2_name}_passing_validaiton.csv"
                )
                self.report.info(
                    f"{df_1_name} validation proof saved to: {df_1_report_name}"
                )
                self.report.info(
                    f"{df_2_name} validation proof saved to: {df_2_report_name}"
                )
                df_1.to_csv(df_1_report_name, index=True)
                df_2.to_csv(df_2_report_name, index=True)
            else:
                self.report.error(f"Found differences in {len(row_diff)} rows!:")
                self.report.error(f"\n{row_diff}")
                self.report.error(f"{'='*80}")
                self.report.error("DETAILED DIFFERENCES:")
                self.report.error(f"{'='*80}")
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
                    for col in row_diff.columns.levels[0]:  # Get the base column names
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
                comparison_filename = f"{self.report.file_name}_comparison.csv"
                errored_filename_df1 = (
                    f"{self.report.file_name}_{df_1_name}_failed_validation.csv"
                )
                errored_filename_df2 = (
                    f"{self.report.file_name}_{df_2_name}_failed_validation.csv"
                )
                row_diff.to_csv(comparison_filename, index=True)
                self.report.info(f"Comparison report saved to: {comparison_filename}")
                df_1.to_csv(errored_filename_df1, index=True)
                self.report.info(f"{df_1_name} report saved to: {errored_filename_df1}")
                df_2.to_csv(errored_filename_df2, index=True)
                self.report.info(f"{df_2_name} report saved to: {errored_filename_df2}")
        except Exception as e:
            self.report.exception(f"Could not log comparison data:\n{e}")

    def _find_missing_rows(
        self,
        df_1: pd.DataFrame,
        df_2: pd.DataFrame,
        df_1_name: str = "df_1",
        df_2_name: str = "df_2",
        key_column: str = "Name",
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Find rows that exist in one data frame but not the other.
        Returns (rows_only_in_df_1, rows_only_in_df_2)
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
            self.report.error(f"{'='*80}")
            self.report.error(f"Row differences based on '{key_column}' column")
            self.report.error("Review the following files and correct inconsistencies.")
            # If df_1 has keys not in df_2
            if len(df_1_only_keys) > 0:
                self.report.info(
                    f"Found {len(df_1_only_rows)} rows ONLY in {df_1_name}:"
                )
                self.report.info(f"{'='*80}")
                # Iterate through the data frame rows
                for index, row in df_1_only_rows.iterrows():
                    self.report.info(f"Row {index}:")
                    for col in df_1_only_rows.columns:
                        self.report.info(f"  {col}: {row[col]}")
                    self.report.info(f"{'-'*40}")
                df_1_rows_filename = (
                    f"{self.report.file_name}_{df_1_name}_only_rows.csv"
                )
                df_1_only_rows.to_csv(df_1_rows_filename, index=False)
                self.report.info(f"Exported to: {df_1_rows_filename}")
            else:
                self.report.info(f"No rows found exclusively in {df_1_name}")
            # If df_2 has keys not in df_1
            if len(df_2_only_keys) > 0:
                self.report.info(
                    f"Found {len(df_2_only_rows)} rows ONLY in {df_2_name}:"
                )
                self.report.info(f"{'-'*80}")
                # Iterate through the data frame rows
                for index, row in df_2_only_rows.iterrows():
                    self.report.info(f"Row {index}:")
                    for col in df_2_only_rows.columns:
                        self.report.info(f"  {col}: {row[col]}")
                    self.report.info(f"{'-'*40}")
                df_2_rows_filename = (
                    f"{self.report.file_name}_{df_2_name}_only_rows.csv"
                )
                df_2_only_rows.to_csv(df_2_rows_filename, index=False)
                self.report.info(f"Exported to: {df_2_rows_filename}")
            else:
                self.report.info(f"No rows found exclusively in {df_2_name}")
            self.report.info(f"{'='*80}")
            # Log number of common rows
            common_keys = df_1_keys & df_2_keys
            self.report.info(f"{len(common_keys)} rows exist in BOTH dataframes")
            return df_1_only_rows, df_2_only_rows  # type: ignore
        except Exception as e:
            self.report.exception(
                f"There was a problem returning the row comparison:\n{e}"
            )
            return pd.DataFrame(), pd.DataFrame()

    def _compare_shapes(
        self,
        df_1: pd.DataFrame,
        df_2: pd.DataFrame,
        df_1_name: str = "df_1",
        df_2_name: str = "df_2",
    ) -> dict | None:
        """
        Compare shapes of two dataframes and return difference information.
        Returns a dictionary with shape comparison details.
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
        self.report.info(f"{'='*80}")
        self.report.info(f"DATAFRAME SHAPE COMPARISON: {df_1_name} vs {df_2_name}")
        self.report.info(f"{'='*80}")
        self.report.info(f"{df_1_name} shape: {shape_1[0]} rows × {shape_1[1]} columns")
        self.report.info(f"{df_2_name} shape: {shape_2[0]} rows × {shape_2[1]} columns")
        # If either data frame shape is 0, fail the validation.
        if shape_1[0] == 0 or shape_2[0] == 0:
            self.report.error(f"{'!'*80}")
            self.report.error("VALIDATION FAILED.")
            self.report.error("A dataframe with no rows was found.")
            self.report.error(
                "Check your filter object name and input files then try again."
            )
            self.report.error(f"{'!'*80}")
            self.report.info(f"{'='*80}")
            return None
        # If the rows from each shape do not match...
        if shape_1[0] != shape_2[0]:
            # Find the number of different rows
            row_diff = abs(shape_1[0] - shape_2[0])
            # Report out the difference
            if shape_1[0] > shape_2[0]:
                self.report.info(
                    f"{df_1_name} has {row_diff} MORE rows than {df_2_name}"
                )
            else:
                self.report.info(
                    f"{df_2_name} has {row_diff} MORE rows than {df_1_name}"
                )
        else:
            self.report.info(f"Row counts match")
        # If the columns from each shape do not match...
        if shape_1[1] != shape_2[1]:
            # Find the number od different columns
            col_diff = abs(shape_1[1] - shape_2[1])
            # Report out the difference
            if shape_1[1] > shape_2[1]:
                self.report.info(
                    f"{df_1_name} has {col_diff} MORE columns than {df_2_name}"
                )
            else:
                self.report.info(
                    f"{df_2_name} has {col_diff} MORE columns than {df_1_name}"
                )
        else:
            self.report.info(f"Column counts match")
        return comparison

    def _normalize_whitespace(
        self, df: pd.DataFrame, columns: list[str] | None = None
    ) -> pd.DataFrame:
        """
        Aggressively normalize whitespace - removes all extra spaces and newlines.
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
            self.report.exception(f"Could not normalize whitespace:\n{e}")
            return df

    def _format_dataframe(
        self, table_type: TableType, df: pd.DataFrame, name_filter: str | None = None
    ) -> pd.DataFrame:
        """
        Helper function that formats and sorts data frames for equality comparisons.
        Returns an empty data frame if an error occurs.
        """
        config_map = {
            TableType.ANALYTICS: {
                "Object Type Order": None,
                "Sort Order": ["Name"],
                "Sort Direction": [True],  # is ascending order
            },
            TableType.CATEGORIES: {
                "Object Type Order": None,
                "Sort Order": ["Name"],
                "Sort Direction": [True],  # is ascending order
            },
            TableType.ELEMENT: {
                "Object Type Order": {"Element": 0, "Attribute": 1},
                "Sort Order": ["Parent", "type_order", "Name"],
                "Sort Direction": [True, False, True],  # is ascending order
            },
            TableType.ELEMENT_TEMPLATE: {
                "Object Type Order": None,
                "Sort Order": ["ObjectType", "Name"],
                "Sort Direction": [False, True],  # is ascending order
            },
            TableType.ENUM_SET: {
                "Object Type Order": {"EnumerationSet": 0, "EnumerationValue": 1},
                "Sort Order": ["Parent", "type_order", "Name"],
                "Sort Direction": [True, True, True],  # is ascending order
            },
            TableType.EVENT_FRAME: {
                "Object Type Order": {"EventFrameTemplate": 0, "AttributeTemplate": 1},
                "Sort Order": ["Parent", "type_order", "Name"],
                "Sort Direction": [True, False, True],  # is ascending order
            },
            TableType.GXP: {
                "Object Type Order": None,
                "Sort Order": ["Name"],
                "Sort Direction": [True],  # is ascending order
            },
            TableType.TABLES: {
                "Object Type Order": {"Table": 0, "TableColumn": 1, "TableDataItem": 2},
                "Sort Order": ["Parent", "type_order", "Name"],
                "Sort Direction": [True, True, True],  # is ascending order
            },
        }
        name_filter = name_filter or None
        try:
            self.report.info("Formatting dataframe...")
            # Setting the table configuration data
            config = config_map[table_type]
            self.report.info(f"Configuration loaded: {config}")
            self.report.info(f"Object table type: {table_type.name}")
            self.report.info(f"Object name filer: {name_filter}")
            # Setting the object type ordering filter
            type_order = config["Object Type Order"]
            if name_filter:
                if table_type in (TableType.ELEMENT_TEMPLATE, TableType.EVENT_FRAME):
                    # Filter mask includes name and parent columns
                    mask = df["Name"].str.contains(
                        name_filter, case=False, na=False
                    ) | df["Parent"].str.contains(name_filter, case=False, na=False)
                elif table_type == TableType.ELEMENT:
                    # Filter mask includes name and template columns
                    mask = df["Name"].str.contains(
                        name_filter, case=False, na=False
                    ) | df["Template"].str.contains(name_filter, case=False, na=False)
                else:
                    # Else, just check the name column
                    mask = df["Name"].str.contains(name_filter, case=False, na=False)
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
            # reset the index
            output = output.reset_index(drop=True)
            # Changing these columns to int helps some data comparison errors.
            numeric_columns = ["AttributeDisplayDigits", "PortMaxConnections"]

            for column in numeric_columns:
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
                    "null": None,
                    "NULL": None,
                    "NaN": None,
                }
            )
            # Change everything to strings for faster comparisons
            output = output.astype("string")
            output = self._normalize_whitespace(output)
            return output
        except Exception as e:
            self.report.exception(f"Could not format dataframe:\n{e}")
            return pd.DataFrame()

    def compare(
        self,
        name_filter: str,
        input_file: str,
        mtl_file: str,
        mtl_worksheet_name: str,
    ) -> bool | None:
        """
        Compare PI builder data to the MTL/CMD. Returns None if process fails.
        """
        if not self.worksheet_metadata[mtl_worksheet_name].can_process:
            self.report.error(
                "This table does not yet have the capability to process data."
            )
            return None
        mtl_table_id = self.worksheet_metadata[mtl_worksheet_name].table_id
        try:
            # Extract the mtl table
            mtl_dataframe = self._get_excel_table(
                mtl_file, mtl_worksheet_name, mtl_table_id
            )
            # drop the version column, new data will not have a version
            mtl_dataframe = mtl_dataframe.drop(columns=["Version"], errors="ignore")
            # read the input csv
            input_csv = pd.read_csv(
                input_file,
                na_values=["None", "none", "NULL", "null", ""],
                keep_default_na=True,
            )
            # sort and format the data
            worksheet_type = self.worksheet_metadata[mtl_worksheet_name].type
            mtl_dataframe = self._format_dataframe(
                worksheet_type, mtl_dataframe, name_filter
            )
            input_dataframe = self._format_dataframe(
                worksheet_type, input_csv, name_filter
            )
            # ensure input data is using the same columns as the mtl
            input_dataframe = input_dataframe[mtl_dataframe.columns]
            # ensure the column data types are the same
            for col in input_dataframe.columns:
                if col in mtl_dataframe.columns:
                    mtl_dataframe[col] = mtl_dataframe[col].astype(  # type: ignore
                        input_dataframe[col].dtype  # type: ignore
                    )
            # Compare DF Shapes
            shape_comparison = self._compare_shapes(
                mtl_dataframe, input_dataframe, "MTL", "Input"  # type: ignore
            )
            # If shape comparison returns none, filter has errored.
            if shape_comparison is None:
                self.report.save()
                return None
            # Find missing rows if shapes differ
            if not shape_comparison["shapes_equal"]:
                self.report.error(f"{'!'*80}")
                self.report.error("VALIDATION FAILED.")
                self.report.error(
                    "Review the following files and correct inconsistencies."
                )
                self.report.error(f"{'!'*80}")
                self._find_missing_rows(
                    mtl_dataframe, input_dataframe, "MTL", "Input", key_column="Name"  # type: ignore
                )
            self._report_comparison(mtl_dataframe, input_dataframe, "MTL", "Input")  # type: ignore
            # Save the report
            self.report.save()
            return True
        except Exception as e:
            self.report.exception(f"Comparison process falied!\n{e}")
            self.report.save()
            return None

    def append(self):
        """
        Add or append new data to the MTL/CMD file.
        """
        logger.critical(f"This function has not yet been created.")
        return None


if __name__ == "__main__":
    FORMAT = "%(asctime)s:%(levelname)s:%(filename)s:%(name)s::%(message)s"
    logging.basicConfig(
        filename="debug_process.log",
        filemode="w",
        format=FORMAT,
        encoding="utf-8",
        level=logging.DEBUG,
    )
    process = Process()
