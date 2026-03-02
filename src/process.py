import logging
import pandas as pd
import openpyxl as xl
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from src.reporting import Reporting
from tkinter.filedialog import askopenfilename as open_file

logger = logging.getLogger(__name__)

# TODO: Report the differing rows in a more human readable way.


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
        self.report_output_path = "reports"
        self.report = Reporting(report_name, output_dir=self.report_output_path)
        self.process_time = datetime.now()
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
            "CMD-Elements-Build": TableInfo("Table11", True, TableType.ELEMENT),
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
        try:
            logger.info(
                f"Extracting excel table {table_id} from worksheet {worksheet_name}..."
            )
            workbook = xl.load_workbook(file_name, data_only=True)
            logger.info("Loaded workbook.")
            worksheet = workbook[worksheet_name]
            # return the cell range of the named table
            data_range = worksheet.tables[table_id].ref
            logger.info("Loaded table.")
            # return a 2d array of table data
            table = [[cell.value for cell in row] for row in worksheet[data_range]]  # type: ignore
            # get header and row data
            headers = table[0]
            rows = table[1:]
            logger.info("Retrieved table data!")
            # create the data frame
            dataframe = pd.DataFrame(rows, columns=headers)  # type: ignore
            logger.info("Data frame created.")
            workbook.close()
            logger.info("Workbook closed.")
            return dataframe
        except Exception as e:
            logger.error(f"Could not extract excel table into a data frame: {e}")
            return pd.DataFrame()

    def _log_append(
        self,
        df: pd.DataFrame,
    ):
        """
        Prints and logs the data added to the MTL.
        """
        header = f"=== LOGGING APPENDED DATA ==="
        logger.info(header)
        self.report._add_line(header)
        try:
            df.to_csv("appended.csv", index=True)
            logger.info(df)
            logger.info("Appended data logged.")
        except Exception as e:
            logger.error(f"Could not export appended data: {e}")

    def _debug_dataframe(self, df, df_name=None):
        """
        Debug helper function that prints the data frame,
        shape, index list, and dtypes of the supplied data frame.
        """
        if df_name is None:
            df_name = "Unknown Frame"
        try:
            self.report.info(f"=== DEBUGGING {df_name} ===")
            self.report.info(df)
            self.report.info(f"{df_name} shape: {df.shape}")
            self.report.info(f"{df_name} index: {df.index.tolist()}")
            self.report.info(f"{df_name} columns:\n{df.columns}")
            self.report.info(f"{df_name} dtypes:\n{df.dtypes}")
        except Exception as e:
            self.report.exception(f"Could not debug dataframe:\n{e}")
        finally:
            self.report.save()

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
            for col in columns:
                if col in df_copy.columns:
                    # Replace all whitespace (spaces, tabs, newlines) with single space
                    df_copy[col] = df_copy[col].str.replace(r"\s+", " ", regex=True)
                    # Strip leading/trailing whitespace
                    df_copy[col] = df_copy[col].str.strip()

            return df_copy
        except Exception as e:
            logger.error(f"Could not normalize whitespace: {e}")
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
        try:
            logger.info("Formatting dataframe...")
            config = config_map[table_type]
            logger.info(f"Configuration loaded: {config}")
            name_filter = name_filter or None
            logger.info(f"Name column filer: {name_filter}")
            type_order = config["Object Type Order"]
            if name_filter:
                if table_type == TableType.ELEMENT_TEMPLATE:
                    mask = df["Name"].str.contains(
                        name_filter, case=False, na=False
                    ) | df["Parent"].str.contains(name_filter, case=False, na=False)
                else:
                    mask = df["Name"].str.contains(name_filter, case=False, na=False)
                output = df.loc[mask].copy()
            else:
                output = df.copy()
            if type_order is not None:
                output["type_order"] = output["ObjectType"].map(type_order)  # type: ignore
            output = output.sort_values(
                by=config["Sort Order"],
                ascending=config["Sort Direction"],
                ignore_index=True,
                kind="stable",
            )
            if type_order is not None:
                output = output.drop(columns=["type_order"])
            output = output.reset_index(drop=True)
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
            output = output.astype("string")
            output = self._normalize_whitespace(output)
            return output
        except Exception as e:
            logger.error(f"Could not format dataframe: {e}")
            return pd.DataFrame()

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

        if shape_1[0] == 0 or shape_2[0] == 0:
            self.report.error("A dataframe with no rows was found.")
            self.report.error("Check your filter object name, and input files.")
            self.report.error("Validation Cancelled.")
            return None

        if shape_1[0] != shape_2[0]:
            diff = abs(shape_1[0] - shape_2[0])
            if shape_1[0] > shape_2[0]:
                self.report.info(f"{df_1_name} has {diff} MORE rows than {df_2_name}")
            else:
                self.report.info(f"{df_2_name} has {diff} MORE rows than {df_1_name}")
        else:
            self.report.info(f"Row counts match")

        if shape_1[1] != shape_2[1]:
            diff = abs(shape_1[1] - shape_2[1])
            if shape_1[1] > shape_2[1]:
                self.report.info(
                    f"{df_1_name} has {diff} MORE columns than {df_2_name}"
                )
            else:
                self.report.info(
                    f"{df_2_name} has {diff} MORE columns than {df_1_name}"
                )
        else:
            self.report.info(f"Column counts match")

        return comparison

    def _find_missing_rows(
        self,
        df_1: pd.DataFrame,
        df_2: pd.DataFrame,
        df_1_name: str = "df_1",
        df_2_name: str = "df_2",
        key_column: str = "Name",
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Find rows that exist in one dataframe but not the other.
        Returns (rows_only_in_df_1, rows_only_in_df_2)
        """
        try:
            # Get unique identifiers from both dataframes
            keys_1 = set(df_1[key_column].dropna().unique())
            keys_2 = set(df_2[key_column].dropna().unique())

            # Find differences
            only_in_df_1 = keys_1 - keys_2
            only_in_df_2 = keys_2 - keys_1

            # Get the actual rows
            rows_only_in_df_1 = df_1[df_1[key_column].isin(only_in_df_1)]
            rows_only_in_df_2 = df_2[df_2[key_column].isin(only_in_df_2)]

            # Log findings
            self.report.info(f"{'*'*80}")
            self.report.info("Row differences found!")
            self.report.info("Validation FAILED.")
            self.report.info("Review the following files and correct inconsistencies.")
            self.report.info(f"{'='*80}")
            self.report.info(f"ROW DIFFERENCES (based on '{key_column}' column)")
            self.report.info(f"{'='*80}")

            if len(only_in_df_1) > 0:
                self.report.info(
                    f"Found {len(rows_only_in_df_1)} rows ONLY in {df_1_name}:"
                )
                self.report.info(f"{'='*80}")
                # Itterate through the data frame rows
                for index, row in rows_only_in_df_1.iterrows():
                    self.report.info(f"Row {index}:")
                    for col in rows_only_in_df_1.columns:
                        self.report.info(f"  {col}: {row[col]}")
                    self.report.info(f"{'-'*40}")
                rows_only_in_df_1.to_csv(f"rows_only_in_{df_1_name}.csv", index=False)
                self.report.info(f"Exported to: rows_only_in_{df_1_name}_dataframe.csv")
                self.report.info(f"{'+'*80}")
            else:
                self.report.info(f"No rows found exclusively in {df_1_name}")
                self.report.info(f"{'+'*80}")

            if len(only_in_df_2) > 0:
                self.report.info(
                    f"Found {len(rows_only_in_df_2)} rows ONLY in {df_2_name}:"
                )
                self.report.info(f"{'-'*80}")
                # Itterate through the data frame rows
                for index, row in rows_only_in_df_2.iterrows():
                    self.report.info(f"Row {index}:")
                    for col in rows_only_in_df_2.columns:
                        self.report.info(f"  {col}: {row[col]}")
                    self.report.info(f"{'-'*40}")
                rows_only_in_df_2.to_csv(f"rows_only_in_{df_2_name}.csv", index=False)
                self.report.info(f"Exported to: rows_only_in_{df_2_name}_dataframe.csv")
                self.report.info(f"{'+'*80}")
            else:
                self.report.info(f"No rows found exclusively in {df_2_name}")
                self.report.info(f"{'+'*80}")

            # Log common rows
            common_keys = keys_1 & keys_2
            self.report.info(f"{len(common_keys)} rows exist in BOTH dataframes")

            return rows_only_in_df_1, rows_only_in_df_2

        except Exception as e:
            self.report.error(f"Could not find missing rows: {e}")
            return pd.DataFrame(), pd.DataFrame()

    def _log_comparison(
        self,
        df_1: pd.DataFrame,
        df_2: pd.DataFrame,
        df_1_name: str = "df_1",
        df_2_name: str = "df_2",
    ):
        """
        Logs the differences in the supplied data frames.
        """
        try:
            self.report.info(f"{'='*80}")
            self.report.info(f"FULL COMPARISON: {df_1_name} vs {df_2_name}")
            self.report.info(f"{'='*80}")

            # Inital equality check
            data_is_equal = df_1.equals(df_2)
            if data_is_equal:
                self.report.info("Data structure is Equal!")
            else:
                self.report.error("Data structure is Not Equal!")
                self.report.error("Check the following data for inconsistencies.")

            # If data frame shapes do not match
            self.report.info("Checking data frame shapes.")
            if df_1.shape != df_2.shape:
                self.report.error(
                    "DataFrames of the supplied data have different shapes."
                )
                self.report.error("VALIDATION CANCELLED.")
                self.report.error(
                    "Review supplied comparison data and make the appropriate changes."
                )

                # Only compare common rows if row counts differ
                if df_1.shape[0] != df_2.shape[0]:
                    min_rows = min(df_1.shape[0], df_2.shape[0])
                    self.report.warning("Row counts differ...")
                    self.report.warning(f"Comparing first {min_rows} rows only...")
                    diff = df_1.iloc[:min_rows].compare(
                        df_2.iloc[:min_rows],
                        align_axis=1,
                        result_names=(df_1_name, df_2_name),
                    )
                else:
                    self.report.info("Row counts the same...")
                    self.report.info("Continuing with full comparisons.")
                    diff = df_1.compare(
                        df_2, align_axis=1, result_names=(df_1_name, df_2_name)
                    )
            else:
                diff = df_1.compare(
                    df_2, align_axis=1, result_names=(df_1_name, df_2_name)
                )

            if diff.empty:
                self.report.info("No differences found in common rows!")
                self.report.info(f"Validation of {df_1_name} to {df_2_name} is sound!")
                self.report.info(f"See reporting for detailed breakdown.")
                df_1.to_csv(f"validated_{df_1_name}_dataframe.csv", index=True)
                df_2.to_csv(f"validated_{df_2_name}_dataframe.csv", index=True)
            else:
                self.report.info(f"Found {len(diff)} rows with differences:")
                self.report.info(f"\n{diff}")
                diff.to_csv(f"{self.report.report_name}_differences.csv", index=True)
                self.report.info(
                    f"Exported to: {self.report.report_name}_differences.csv"
                )
                df_1.to_csv(f"errored_{df_1_name}_dataframe.csv", index=True)
                df_2.to_csv(f"errored_{df_2_name}_dataframe.csv", index=True)

        except Exception as e:
            self.report.exception(f"Could not log comparison data:\n{e}")

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
            logger.error("This table does not yet have the capability to process data.")
            return None
        mtl_table_id = self.worksheet_metadata[mtl_worksheet_name].table_id
        try:
            # extract the mtl table
            mtl_dataframe = self._get_excel_table(
                mtl_file, mtl_worksheet_name, mtl_table_id
            )
            # drop the version column, new data will not have a version
            mtl_dataframe = mtl_dataframe.drop(columns=["Version"])
            # extract the input data
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
                mtl_dataframe, input_dataframe, "MTL", "Input"
            )
            # If shape comparison returns none, filter has errored.
            if shape_comparison is None:
                self.report.save()
                return None
            # Find missing rows if shapes differ
            if not shape_comparison["shapes_equal"]:
                self._find_missing_rows(
                    mtl_dataframe, input_dataframe, "MTL", "Input", key_column="Name"
                )
            else:
                self._log_comparison(mtl_dataframe, input_dataframe, "MTL", "Input")  # type: ignore
            # Save the report
            self.report.save()
            return True
        except Exception as e:
            self.report.exception(f"Comparison falied!\n{e}")
            self.report.save()
            return None

    def append(self):
        """
        Add or append new data to the MTL/CMD file.
        """
        logger.critical(f"This function has not yet been created.")
        return None

    def test(self):
        name = "Jaffrey Equipment"
        worksheet = "CMD-Element Templates-VAL"
        logger.debug("=== Process class test function started. ===")
        logger.debug(f"=== Name column tested: {name} ===")
        logger.debug(f"Worksheet tested: {worksheet}")
        excel_filetypes = [
            ("Supported files", ("*.xlsx", "*.xlsm")),
        ]
        input_filetypes = [
            ("Input files", ("*.csv")),
        ]
        test_input = open_file(
            title="Select your new data file.",
            filetypes=input_filetypes,
        )
        test_mtl = open_file(
            title="Select the MTL/CMD file.", filetypes=excel_filetypes
        )
        logger.debug(f"Input path: {test_input}")
        logger.debug(f"MTL Path: {test_mtl}")
        self.compare(
            name,
            test_input,
            test_mtl,
            worksheet,
        )


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
    process.test()
