# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
#
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH

# third party
import pandas as pd
import xlwings as xl

# local
from src.reporting import Reporting
from src.metadata import AppMetadata


class DataExtractor:
    """
    A data extraction class that helps pull data from excel and csv files for processing
    within the WAVE tool.
    """

    def __init__(self, report: Reporting, metadata: AppMetadata) -> None:
        self.report = report
        self.metadata = metadata

    def extract_mtl_table(self, mtl_file_path: str) -> pd.DataFrame:
        """
        Returns a data frame from a named excel table in the MTL.
        Will raise an exception if it fails.
        This iteration uses xlwings as the extractor. xlwings opens an instance of
        excel and data runs through the app instance. Slower but directly interacts
        with an active version of excel.
        """
        dataframe = pd.DataFrame()
        try:
            excel = xl.App(visible=False)
            workbook = excel.books.open(mtl_file_path)
            worksheet = workbook.sheets[self.metadata.get_worksheet_name()]
            table = worksheet.tables[self.metadata.get_table_id()]
            dataframe: pd.DataFrame = table.range.options(
                pd.DataFrame, header=True, index=False
            ).value
            self.report.info("MTL Data extracted successfully.")
            return dataframe
        except Exception as e:
            self.report.error("MTL extraction with xlwings failed.")
            self.report.exception(f"{e}")
            return dataframe
        finally:
            if workbook:
                workbook.close()
            if excel:
                excel.quit()

    def extract_input_csv(
        self,
        file_path: str,
        filter_str: str,
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
            self.report.info("Input extraction was successful!")
            return df
        except UnicodeDecodeError as e:
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
                fixed_name = f"{filter_str}_fixed.csv"
                fixed_file = self.report.report_folder / fixed_name
                df.to_csv(fixed_file, encoding="utf-8-sig", index=False)
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
                self.report.highlight_error("Could not convert bad input data.")
                self.report.critical(error_msg, popup=True)
                return None
        except Exception as e:
            error_msg = (
                f"Input extraction unknown exception. Please report this error.\n{e}"
            )
            self.report.highlight_error("Could not convert bad input data.")
            self.report.critical(error_msg, popup=True)
            return None

    def could_extract(
        self, mtl_dataframe: pd.DataFrame | None, input_dataframe: pd.DataFrame | None
    ) -> bool:
        if mtl_dataframe is None:
            self.report.highlight_titled_error(
                " MTL data could not be extracted. Check your selected MTL table."
            )
            return False
        if input_dataframe is None:
            self.report.highlight_titled_error(
                " Input CSV could not be extracted. Check your selected input table"
            )
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
