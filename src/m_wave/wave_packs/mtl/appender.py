# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
#
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH

# stdlib
import time
from pathlib import Path

# third party
import pandas as pd
import xlwings as xl
import pywintypes

# local core
from m_wave.core.reporting import Reporting

# local wave pack
from m_wave.wave_packs.mtl.metadata import Metadata


class DataAppender:
    def __init__(
        self,
        report: Reporting,
        metadata: Metadata,
    ) -> None:
        self.report = report
        self.metadata = metadata

    def upsert(
        self,
        mtl_dataframe: pd.DataFrame,
        input_dataframe: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Update and insert a input_dataframe into the mtl_dataframe, matching on `keys`
        (list of column names). input_dataframe values overwrite mtl_dataframe for
        matching keys; new keys are appended. All columns conform to the MTL and input
        columns are silently dropped. Returns empty data frame if it fails.
        """
        output = pd.DataFrame()
        try:
            # get keys of new rows to append
            keys = self.metadata.get_table_index_keys()
            original_columns = mtl_dataframe.columns

            keyed_mtl = mtl_dataframe.set_index(keys)
            keyed_input = input_dataframe.set_index(keys)

            # Save each data frame to keep record of the changes.
            mtl_dataframe.to_csv(
                self.report.report_folder / "mtl_dataframe_before.csv", index=False
            )
            input_dataframe.to_csv(
                self.report.report_folder / "input_dataframe.csv", index=False
            )

            keyed_mtl = keyed_mtl[~keyed_mtl.index.isin(keyed_input.index)]
            output = pd.concat([keyed_mtl, keyed_input]).reset_index()[original_columns]

            dropped = set(input_dataframe.columns) - set(original_columns)
            if dropped:
                self.report.warning(
                    "The following input columns were dropped during upsert:"
                )
                for i in dropped:
                    self.report.warning(f"\t{i}")

            return output  # type: ignore

        except KeyError as e:
            error_msg = f"A key error occurred during upserting.\n{e}"
            self.report.exception(error_msg)
            return output  # type: ignore

        except ValueError as e:
            error_msg = f"A value error occurred during upserting.\n{e}"
            self.report.exception(error_msg)
            return output  # type: ignore

        except Exception as e:
            error_msg = f"An unexpected error occurred during upserting.\n{e}"
            self.report.exception(error_msg)
            return output  # type: ignore

    def export_to_csv(self, appended_dataframe: pd.DataFrame) -> None:
        """
        Used to export the new appended data frame to csv format.
        """
        appended_filename = "mtl_dataframe_after.csv"
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
        retries: int = 3,
        delay: float = 3.0,
    ) -> None:
        """
        Supply a data frame that will attempt to replace the corresponding table in the
        mtl. Retries saving the new copy for OLE Busy errors (likely OneDrive problems).
        """
        if not output_file_path:
            doc_num = self.metadata.get_mtl_doc_num()
            output_file_path = self.report.report_folder / f"{doc_num}_appended.xlsx"

        table_id = self.metadata.get_table_id()
        worksheet_name = self.metadata.get_worksheet_name()

        excel = None
        workbook = None

        try:
            self.report.info("Attempting to update the MTL.")

            excel = xl.App(visible=False, add_book=False)
            self.report.info("Excel opened silently.")

            workbook = excel.books.open(mtl_file_path, read_only=True)
            self.report.info("Workbook found.")

            self.report.info("Saving a working copy...")
            for attempt in range(retries):
                try:
                    self.report.info(f"Save attempt {attempt + 1} of {retries}.")
                    workbook.save(output_file_path)
                    break
                except pywintypes.com_error as e:
                    if e.args[0] == -2146777998:  # OLE Busy
                        if attempt < retries - 1:
                            time.sleep(delay)
                            continue
                    raise
            else:
                raise RuntimeError(f"Failed to save workbook after {retries} attempts.")

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
            self.report.info(f"MTL Saved to a new file at: ../{output_file_path.name}")

        except Exception as e:
            self.report.error(
                "Failed to export the data to the MTL. Check your logs.", popup=True
            )
            self.report.exception(f"\n{e}")

        finally:
            if workbook is not None:
                workbook.close()
                self.report.debug("Workbook should be closed.", report=False)
            if excel is not None:
                excel.quit()
                self.report.debug("Excel should be closed.", report=False)
