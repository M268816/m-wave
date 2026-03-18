# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
#
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH

# third party
import pandas as pd
import openpyxl as xl

# local
from src.reporting import Reporting


class DataExtractor:
    """
    A data extraction class that helps pull data from excel and csv files for processing
    within the WAVE tool.
    """

    def __init__(self, report: Reporting) -> None:
        self.report = report

    def extract_mtl_table(
        self,
        file_name: str,
        worksheet_name: str,
        table_id: str,
    ) -> pd.DataFrame | None:
        """
        Returns a data frame from a named excel table in the MTL.
        Will raise an exception if it fails.
        """
        workbook = None
        try:
            self.report.info("Extracting the MTL table...")
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
            if workbook is not None:
                workbook.close()
                self.report.info("Workbook closed.")

    def extract_input_csv(
        self,
        file_path: str,
        filter: str,
    ) -> pd.DataFrame | None:
        """
        Returns a data frame from an input csv file.
        Will raise an exception if it fails.
        """
        # Read the input csv
        try:
            self.report.info("Extracting the Input file.")
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
