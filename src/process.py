# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
#
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH

# stdlib
import logging

# third party
import ttkbootstrap as ttk

# local
from src.data_extraction import DataExtractor
from src.data_formatter import DataFormatter
from src.data_comparator import DataComparator
from src.metadata import WORKSHEET_METADATA
from src.paths import REPORTS_DIR
from src.reporting import Reporting

logger = logging.getLogger(__name__)


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
        self.worksheet_metadata = WORKSHEET_METADATA
        self.data_extractor = DataExtractor(self.report)
        self.data_formatter = DataFormatter(self.report)
        self.data_comparator = DataComparator(self.report)

    def compare_datasets(
        self,
        filter_str: str,
        input_file: str,
        mtl_file: str,
        mtl_worksheet_name: str,
    ) -> bool | None:
        """
        Compare the supplied PI builder data and the MTL/CMD.
        Returns None if process fails.
        """
        # TODO: Filter down Input columns to MTL columns
        try:
            # NOTE: START THE COMPARISON
            self.report.title(f"COMPARISON STARTED FOR: {filter_str or 'None'}")

            # Check if the table cane processed.
            if not self.data_comparator.can_process(mtl_worksheet_name):
                return None

            # Gather MTL Table metadata
            mtl_table_id = self.worksheet_metadata[mtl_worksheet_name].table_id
            mtl_worksheet_type = self.worksheet_metadata[mtl_worksheet_name].type

            self.report.debug(f"Selected worksheet: {mtl_worksheet_name}")
            self.report.debug(f"Table type: {mtl_worksheet_type.name}")
            self.report.debug(f"Filtering data with string: {filter_str or 'None'}")

            # NOTE: EXTRACTION PHASE
            self.report.title(
                "Extraction Phase: Extracting data sources into data frames."
            )
            mtl_dataframe = self.data_extractor.extract_mtl_table(
                mtl_file, mtl_worksheet_name, mtl_table_id
            )
            input_dataframe = self.data_extractor.extract_input_csv(
                input_file, filter_str
            )
            if not self.data_comparator.could_extract(mtl_dataframe, input_dataframe):
                return None

            # NOTE: FORMATTING PHASE 1
            self.report.title(
                "Formatting Phase (1 of 2): Preparing data for comparison."
            )

            # Format the dataframes to the worksheet table type.
            self.report.info("Formatting MTL dataframe...")
            mtl_dataframe = self.data_formatter.format(
                mtl_worksheet_type, mtl_dataframe, filter_str  # type: ignore
            )
            self.report.info("Formatting INPUT CSV dataframe...")
            input_dataframe = self.data_formatter.format(
                mtl_worksheet_type, input_dataframe, filter_str
            )

            if not self.data_comparator.could_format(mtl_dataframe, input_dataframe):
                return None

            # NOTE: FORMATTING PHASE 2
            self.report.title(
                "Formatting Phase (2 of 2): Conforming input columns to MTL standard."
            )
            conform_result = self.data_formatter.conform_columns(
                mtl_dataframe, input_dataframe
            )
            if conform_result is None:
                return None
            # Apply the conforming process to the working data frames.
            mtl_dataframe, input_dataframe = conform_result

            # NOTE: COMPARISON PHASE
            self.report.title("Comparison Phase: Comparing data frames.")
            shape_comparison = self.data_comparator.compare_shapes(
                mtl_dataframe, input_dataframe, "MTL", "Input CSV"
            )
            if shape_comparison is None:
                return None

            # NOTE: REPORTING PHASE
            self.report.title("Reporting Phase: Detailed report of any issues.")
            self.data_comparator.comparison_report(
                mtl_dataframe, input_dataframe, "MTL", "Input"
            )
            self.report.title("FINISHED")
            self.report.info("Comparison checks completed.")
            self.report.info(
                "Review the generated .LOG and CSV files for detailed results."
            )
            return True
        except Exception as e:
            self.report.exception(
                f"Unexpected error during comparison logic:\n{e}", popup=True
            )
            return None

        finally:
            self.report.save_report()

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
