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
    The processes of this app have the ability to retrieve named table data from the
    MTL/CMD excel sheet and PI Builder data in CSV format.

    This process will extract the data in to pandas data frames then format and sort
    each data frame to the user selected MTL table.

    The process will then either:
        compare the data:
            by filtering the data frames to a user submitted object string, or a full
            comparison will be conducted if no filter is given.
        append new data to the MTL:
            !!! Not yet implemented. !!!
            by comparing the MTL and either updating existing rows, or adding new rows.
    """

    def __init__(
        self,
        report: Reporting,
    ) -> None:
        self.report = report
        self.data_extractor = DataExtractor(self.report)
        self.data_formatter = DataFormatter(self.report)
        self.data_comparator = DataComparator(self.report)

    def _can_process(self, worksheet_name: str) -> bool:
        """
        Check a MTL worksheet by name and determine if it can be processed.
        """
        if not WORKSHEET_METADATA[worksheet_name].can_process:
            self.report.highlight_titled_error(
                "✗ This table does not yet have the capability to process data.",
            )
            self.report.save_report()
            return False
        return True

    def compare_datasets(
        self,
        filter_str: str,
        input_filepath: str,
        mtl_filepath: str,
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

            # Check if the table can processed.
            if not self._can_process(mtl_worksheet_name):
                return None

            # NOTE: EXTRACTION PHASE
            self.report.title(
                "Extraction Phase: Extracting data sources into data frames."
            )
            mtl_dataframe = self.data_extractor.extract_mtl_table(
                mtl_filepath, mtl_worksheet_name
            )
            input_dataframe = self.data_extractor.extract_input_csv(
                input_filepath, filter_str
            )
            if not self.data_extractor.could_extract(mtl_dataframe, input_dataframe):
                return None

            # NOTE: FORMATTING PHASE 1
            self.report.title("Formatting Phase: Preparing data for comparison.")

            # Format the data frames to the worksheet table type.
            self.report.info("Formatting MTL dataframe...")
            mtl_dataframe = self.data_formatter.format(
                mtl_worksheet_name, mtl_dataframe, filter_str  # type: ignore
            )
            self.report.info("Formatting INPUT CSV dataframe...")
            input_dataframe = self.data_formatter.format(
                mtl_worksheet_name, input_dataframe, filter_str
            )

            if not self.data_formatter.could_format(mtl_dataframe, input_dataframe):
                return None

            # NOTE: COMPARISON PHASE 1: GENERAL
            self.report.title(
                "Comparison Phase (1 of 2): General Data Frame Shape Comparison"
            )
            shape_comparison = self.data_comparator.compare_shapes(
                mtl_dataframe, input_dataframe
            )
            if shape_comparison is None:
                return None
            self.report.info("Shape comparison completed:")
            for key, value in shape_comparison.items():
                self.report.info(f"    {key}: {value}")

            # NOTE: COMPARISON PHASE 2: COLUMNS
            self.report.title(
                "Comparison Phase (2 of 3): Comparing columns and making adjustments."
            )
            conform_result = self.data_comparator.conform_columns(
                mtl_dataframe, input_dataframe
            )
            if conform_result is None:
                return None

            # Apply the conforming process to the working data frames.
            mtl_dataframe, input_dataframe = conform_result

            # NOTE: COMPARISON PHASE 3: ROWS
            self.report.title("Comparison Phase (3 of 3): Comparing data frames.")
            row_comparison = self.data_comparator.compare_rows(
                mtl_dataframe,
                input_dataframe,
            )
            if row_comparison is None:
                return None

            # NOTE: REPORT PHASE
            self.report.title("Final Reports")
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
