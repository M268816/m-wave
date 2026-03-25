# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
#
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH

# stdlib
import logging

# third party
import ttkbootstrap as ttk

# local
from src.data_appender import DataAppender
from src.data_extraction import DataExtractor
from src.data_formatter import DataFormatter
from src.data_comparator import DataComparator
from src.metadata import AppMetadata
from src.paths import REPORTS_DIR
from src.reporting import Reporting

logger = logging.getLogger(__name__)


class Process:
    """
    This process shall attempt to extract MTL named tables and CSV input files into
    data frames. These extracted data frames will then be formatted and sorted
    according to the formatting style of the MTL.

    The comparison function shall attempt to compare the MTL to the input and report
    to the user if the comparison is sound or has differences. These differences shall
    be reported to the user in the form of log files and exported csv files of the data
    frames that were compared. This comparison shall be able to compare full MTL table
    data along with a user supplied 'object name' that shall attempt to filter each
    data frame.

    The append function shall attempt to append and update the MTL data frame with
    the input file. The appended or updated data, known as an upsert, shall be reported
    to the user with exported log and csv files. The append function shall attempt to
    apply these upserts to the MTL directly as well. The user will be  responsible for
    updating the change log manually.
    """

    def __init__(
        self,
        report: Reporting,
        filter_string: str,
        selected_data_table: str,
        mtl_file_path: str,
        input_file_path: str,
    ) -> None:
        self.report = report
        self.filter_string = filter_string
        self.mtl_worksheet_name = selected_data_table
        self.mtl_file_path = mtl_file_path
        self.input_file_path = input_file_path
        self.data_appender = DataAppender(self.report, self.mtl_worksheet_name)
        self.data_extractor = DataExtractor(self.report, self.mtl_worksheet_name)
        self.data_formatter = DataFormatter(self.report, self.mtl_worksheet_name)
        self.data_comparator = DataComparator(self.report, self.mtl_worksheet_name)
        self.metadata = AppMetadata(self.mtl_worksheet_name)

    def _can_process(self) -> bool:
        """
        Check a MTL worksheet by name and determine if it can be processed.
        """
        can_process = self.metadata.can_process_worksheet()
        if not can_process:
            self.report.highlight_titled_error(
                "✗ This table does not yet have the capability to process data.",
            )
            self.report.error("Stopping process...")
            self.report.save_report()
            return False
        return True

    def compare_input(self) -> bool | None:
        """
        Compare the supplied PI builder data and the MTL/CMD.
        Returns None if process fails.
        """
        try:
            # NOTE: START THE COMPARISON
            self.report.title(
                f"COMPARISON STARTED FOR: {self.filter_string or 'None'} within {self.mtl_worksheet_name}"
            )

            # Check if the table can processed.
            if not self._can_process():
                return None

            # NOTE: EXTRACTION PHASE
            self.report.simple_title(
                "Extraction Phase: Extracting data sources into data frames."
            )
            mtl_dataframe = self.data_extractor.extract_mtl_table(self.mtl_file_path)
            input_dataframe = self.data_extractor.extract_input_csv(
                self.input_file_path, self.filter_string
            )
            if not self.data_extractor.could_extract(mtl_dataframe, input_dataframe):
                return None

            # NOTE: FORMATTING PHASE
            self.report.simple_title(
                "Formatting Phase (1 of 2): Preparing data for comparison."
            )

            # Format the data frames to the worksheet table type.
            self.report.info("Formatting MTL dataframe...")
            mtl_dataframe = self.data_formatter.format(
                self.mtl_worksheet_name, mtl_dataframe, self.filter_string  # type: ignore
            )
            self.report.info("Formatting INPUT CSV dataframe...")
            input_dataframe = self.data_formatter.format(
                self.mtl_worksheet_name,
                input_dataframe,
                self.filter_string,
            )

            if not self.data_formatter.could_format(mtl_dataframe, input_dataframe):
                return None

            # NOTE: FORMATTING PHASE 2: COLUMNS
            self.report.simple_title(
                "Formatting Phase (2 of 2): Comparing columns and making adjustments."
            )
            conform_result = self.data_formatter.conform_columns(
                mtl_dataframe, input_dataframe
            )
            if conform_result is None:
                return None

            # Apply the conforming process to the working data frames.
            mtl_dataframe, input_dataframe = conform_result

            # NOTE: COMPARISON PHASE 2: GENERAL COMPARISON
            self.report.simple_title(
                "Comparison Phase (1 of 2): General Data Frame Comparison, Sanity Check"
            )
            shape_comparison = self.data_comparator.compare_shapes(
                mtl_dataframe, input_dataframe
            )
            if shape_comparison is None:
                return None
            self.report.info("Shape comparison completed:")
            for key, value in shape_comparison.items():
                self.report.info(f"    {key}: {value}")

            # NOTE: COMPARISON PHASE 3: ROWS
            self.report.simple_title("Comparison Phase (2 of 2): Comparing row data.")
            row_comparison = self.data_comparator.compare_rows(
                mtl_dataframe,
                input_dataframe,
            )
            if row_comparison is None:
                return None

            # NOTE: REPORT PHASE
            self.report.subtitle("Comparison checks completed.")
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

    def append_input(self) -> bool | None:
        """
        Compare the supplied PI builder data and the MTL/CMD.
        Returns None if process fails.
        """
        try:
            # NOTE: START THE COMPARISON
            self.report.title(
                f"APPENDING: {self.filter_string or 'None'} to {self.mtl_worksheet_name}"
            )

            # Check if the table can processed.
            if not self._can_process():
                return None

            # NOTE: EXTRACTION PHASE
            self.report.title(
                "Extraction Phase: Extracting data sources into data frames."
            )
            mtl_dataframe = self.data_extractor.extract_mtl_table(self.mtl_file_path)
            input_dataframe = self.data_extractor.extract_input_csv(
                self.input_file_path, self.filter_string
            )
            if not self.data_extractor.could_extract(mtl_dataframe, input_dataframe):
                return None

            # NOTE: FORMATTING PHASE 1: PREP
            self.report.title(
                "Formatting Phase (1 of 2): Preparing data for comparison."
            )

            # Format the data frames to the worksheet table type.
            self.report.info("Formatting MTL dataframe...")
            mtl_dataframe = self.data_formatter.format(
                self.mtl_worksheet_name, mtl_dataframe, name_filter=None, use_version=True  # type: ignore
            )
            self.report.info("Formatting INPUT CSV dataframe...")
            input_dataframe = self.data_formatter.format(
                self.mtl_worksheet_name,
                input_dataframe,
                self.filter_string,
                use_version=True,
            )

            if not self.data_formatter.could_format(mtl_dataframe, input_dataframe):
                return None

            # NOTE: FORMATTING PHASE 2: COLUMNS
            self.report.title(
                "Formatting Phase (2 of 2): Comparing columns and making adjustments."
            )
            conform_result = self.data_formatter.conform_columns(
                mtl_dataframe, input_dataframe
            )
            if conform_result is None:
                return None

            # Apply the conforming process to the working data frames.
            mtl_dataframe, input_dataframe = conform_result

            # NOTE: COMPARISON PHASE
            self.report.title(
                "Comparison Phase: General Data Frame Comparison, Sanity Check"
            )
            shape_comparison = self.data_comparator.compare_shapes(
                mtl_dataframe, input_dataframe
            )
            if shape_comparison is None:
                return None
            self.report.info("Shape comparison completed:")
            for key, value in shape_comparison.items():
                self.report.info(f"    {key}: {value}")

            # NOTE: APPEND PHASE
            self.report.title("Append Phase: Appending input csv to MTL.")
            appended_dataframe = self.data_appender.upsert(
                mtl_dataframe, input_dataframe
            )
            if appended_dataframe is None:
                return None

            # NOTE: FORMAT NEW APPENDED DATAFRAME TO ALIGN WITH OLD MTL FORMATTING.
            self.report.title(
                "Refromatting Phase: Aligning new data to the old MTL fomat."
            )
            appended_dataframe = self.data_formatter.format(
                self.mtl_worksheet_name,
                appended_dataframe,
                name_filter=None,
                use_version=True,
            )
            if appended_dataframe is None:
                return None

            # NOTE: REPORT PHASE
            self.report.title("Appending completed.")
            self.data_appender.export_to_csv(appended_dataframe)
            self.report.info(
                "Review the generated .LOG and CSV files for detailed results."
            )

            # TEST: Export to Excel
            self.report.title("Attempting to create an appended version of the MTL.")
            self.data_appender.rebuild_named_table_in_place(
                self.mtl_file_path, appended_dataframe
            )

            # FINALLY
            return True

        except Exception as e:
            self.report.exception(
                f"Unexpected error during append logic:\n{e}", popup=True
            )
            return None

        finally:
            self.report.save_report()


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
    process = Process(
        report,
        "",
        "",
        "",
        "",
    )
    process.report.error("This module should not be run as a script.")
    exit()
