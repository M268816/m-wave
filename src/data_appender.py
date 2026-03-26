# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
#
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH

# Test
# from __future__ import annotations

# stdlib
from pathlib import Path

# third party
import pandas as pd
import xlwings as xl

# local
from src.metadata import AppMetadata
from src.reporting import Reporting


class DataAppender:
    def __init__(self, report: Reporting, mtl_worksheet_name: str) -> None:
        self.report = report
        self.metadata = AppMetadata(mtl_worksheet_name)

    def upsert(
        self,
        mtl_dataframe: pd.DataFrame,
        input_dataframe: pd.DataFrame,
    ) -> pd.DataFrame | None:
        """
        Update and insert a input_dataframe into the mtl_dataframe, matching on `keys`
        (list of column names). input_dataframe values overwrite mtl_dataframe for
        matching keys; new keys are appended. Returns None if it fails.
        """
        try:
            # get keys of new rows to append
            keys = self.metadata.get_table_index_keys()

            keyed_mtl = mtl_dataframe.set_index(keys)
            keyed_input = input_dataframe.set_index(keys)

            # Save each data frame to keep record of the changes.
            mtl_dataframe.to_csv(
                self.report.report_folder / "mtl_dataframe_before.csv", index=False
            )
            input_dataframe.to_csv(
                self.report.report_folder / "input_dataframe.csv", index=False
            )

            # update existing composite keys
            # for each index key that exists in both data frames overwrite the values
            # from the input into the mtl
            keyed_mtl.update(keyed_input)

            # add new composite keys
            # pull keys that do not exist in the MTL
            keys_to_add = keyed_input.loc[keyed_input.index.difference(keyed_mtl.index)]
            # append/concat the new keys to the MTL, reset the index.
            output = pd.concat([keyed_mtl, keys_to_add]).reset_index()

            return output
        except KeyError as e:
            error_msg = f"A key error occurred during upserting.\n{e}"
            self.report.exception(error_msg)
            return None
        except ValueError as e:
            error_msg = f"A value error occurred during upserting.\n{e}"
            self.report.exception(error_msg)
            return None
        except Exception as e:
            error_msg = f"An unexpected error occurred during upserting.\n{e}"
            self.report.exception(error_msg)
            return None

    def export_to_csv(self, appended_dataframe: pd.DataFrame) -> None:
        """
        Used to export the new appended data frame to csv format.
        """
        appended_filename = "appended_table.csv"
        appended_filepath = self.report.report_folder / appended_filename
        self.report.info(f"Exporting the appended data to:  {appended_filepath}")
        self.report.info("This data is supplied as the complete mtl table.")
        self.report.info("This includes all appended rows, and updated rows,")
        self.report.info("    along with the full data within the supplied MTL file.")
        appended_dataframe.to_csv(appended_filepath, encoding="utf-8", index=False)

    def export_to_mtl(
        self,
        appended_dataframe: pd.DataFrame,
        mtl_file_path: str,
        output_file_path: Path | None = None,
    ) -> None:
        """
        Supply a data frame that will attempt to replace the corresponding table in the
        mtl.
        """
        if not output_file_path:
            output_file_path = self.report.report_folder / "20171406_appended.xlsx"

        table_id = self.metadata.get_table_id()
        worksheet_name = self.metadata.get_worksheet_name()

        try:
            self.report.info("Attempting to update the MTL.")

            excel = xl.App(visible=True, add_book=False)
            self.report.info("Excel opened silently.")

            workbook: xl.Book = excel.books.open(mtl_file_path, read_only=True)
            self.report.info("Workbook found.")

            self.report.info("Saving a working copy...")
            workbook.save(output_file_path)
            workbook.close()
            self.report.info("Saved...")

            self.report.info("Opening working copy...")
            workbook = excel.books.open(output_file_path, read_only=False)

            worksheet: xl.Sheet = workbook.sheets[worksheet_name]
            self.report.info("Worksheet accessed.")

            table: xl.main.Table = worksheet.tables[table_id]
            self.report.info(f"Table id:{table_id}, selected.")

            table.update(appended_dataframe, index=False)

            self.report.info("Table values updated.")

            workbook.save()
            self.report.info(f"MTL Saved to a new file at: {output_file_path}")

        except Exception as e:
            self.report.error(
                "Failed to export the data to the MTL. Check your logs.", popup=True
            )
            self.report.exception(f"\n{e}")
        finally:
            workbook.close()
            self.report.debug("Workbook should be closed.")
            excel.quit()
            self.report.debug("Excel should be closed.")
