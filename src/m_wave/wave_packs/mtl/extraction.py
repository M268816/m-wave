# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH
# This tool was created with the help of AI.

# stdlib
import json
import os
import shutil
import time
import webbrowser
from pathlib import Path

import openpyxl as opxl

# third party
import pandas as pd
import xlwings as xl

# local core
from m_wave.core.reporting import Reporting

# local wave pack
from m_wave.wave_packs.mtl.metadata import Metadata
from m_wave.wave_packs.mtl.paths import MTL_DOC_DIR

MTL_URL = (
    "https://mango.merckgroup.com/cara/lnk/content/mango_document/2261639/Effective"
)
MTL_DOC_NUMBER = "20471406"
FILE_EXTENSION = ".xlsx"


class DataExtractor:
    """
    A data extraction class that helps pull data from excel and csv files for processing
    within the WAVE tool.
    """

    def __init__(self, report: Reporting, metadata: Metadata) -> None:
        self.report = report
        self.metadata = metadata

    def _get_browser_download_dir(self) -> Path:
        """
        Reads the configured download directory from
        """
        home = os.path.expanduser("~")
        downloads_folder = os.path.join(home, "Downloads")

        candidates = [
            os.path.join(
                os.environ.get("LOCALAPPDATA", ""),
                "Google",
                "Chrome",
                "User Data",
                "Preferences",
            ),
            os.path.join(
                os.environ.get("LOCALAPPDATA", ""),
                "Microsoft",
                "Edge",
                "User Data",
                "Preferences",
            ),
        ]

        self.report.info("Attempting to locate Downloads Directory...")

        for prefs_path in candidates:
            if os.path.exists(prefs_path):
                try:
                    with open(prefs_path, "r", encoding="utf-8") as f:
                        prefs = json.load(f)
                    custom_dir = prefs.get("download", {}).get("default_directory")
                    if custom_dir and os.path.isdir(custom_dir):
                        self.report.info(
                            "Detected custom download directory successfully."
                        )
                        self.report.info(f"Download dir: {custom_dir}")
                        return Path(custom_dir)
                except Exception:
                    pass
        self.report.info("No custom download directory found. Using defaults.")
        return Path(downloads_folder)

    def _get_dl_dir_snapshot(self, dl_folder: Path) -> set:
        """
        Return a set of (filename, size) tuples for all Excel files in the given dl folder.
        """
        result = set()
        try:
            with os.scandir(dl_folder) as entries:
                for entry in entries:
                    if entry.is_file() and entry.name.endswith(FILE_EXTENSION):
                        if not entry.name.endswith((".crdownload", ".part", ".tmp")):
                            result.add((entry.name, entry.stat().st_size))
        except PermissionError:
            pass
        return result

    def _wait_until_stable(self, filepath: Path, stable_sec: int = 2) -> None:
        prev = -1
        while True:
            try:
                curr = os.path.getsize(filepath)
            except FileNotFoundError:
                time.sleep(0.5)
                continue
            if curr == prev:
                time.sleep(stable_sec)
                break
            prev = curr
            time.sleep(0.5)

    def download_mtl(
        self, timeout_interval_sec: int = 1, timeout_sec: int = 90
    ) -> Path | None:
        """
        Sends a request to ManGo to download the current effective version of the MTL.
        Watches the user's download folder, moves and captures new file path.
        Returns the destination filepath to be opened with xlwings
        """
        download_dir = self._get_browser_download_dir()
        dl_snapshot_before = self._get_dl_dir_snapshot(download_dir)
        webbrowser.open(MTL_URL)

        elapsed = 0
        found = None
        while elapsed < timeout_sec:
            time.sleep(timeout_interval_sec)
            elapsed += timeout_interval_sec
            dl_snapshot_after = self._get_dl_dir_snapshot(download_dir)
            new_files = dl_snapshot_after - dl_snapshot_before
            if new_files:
                filename = sorted(new_files, key=lambda x: x[1], reverse=True)[0][0]
                found = os.path.join(download_dir, filename)
                break
            if elapsed % 10 == 0:
                self.report.info(f"\t... waiting({elapsed}s / {timeout_sec}s)")

        if not found:
            self.report.warning("Process timed out, no excel file detected.")
            return None

        self._wait_until_stable(Path(found))

        name, ext = os.path.splitext(os.path.basename(found))
        destination = os.path.join(MTL_DOC_DIR, f"{name}{ext}")

        shutil.move(found, destination)
        self.report.info(
            f"{Path(found).name} moved from {Path(found).parent}"
            + f" to {Path(destination).parent} as {Path(destination).name}"
        )

        return Path(destination)

    def get_last_revision(
        self, filepath: Path, worksheet_name: str = "Revision History"
    ) -> str | None:
        """
        Parses the 'revision history' sheet to find the last revision entry.
        - Column A = Version (whole number, rows may be vertically merged)
        - Columns B-D = Date, Changed By, Description, Reference
        - A1 = merged title, data starts at A2
        - Last entry = last non-empty cell in col A before a blank
        """
        wb = None
        try:
            wb = opxl.load_workbook(filepath, data_only=True)

            # Case-insensitive sheet name search
            sheet = next(
                (wb[s] for s in wb.sheetnames if worksheet_name.lower() in s.lower()),
                None,
            )
            if sheet is None:
                self.report.warning("No 'revision history' sheet found.")
                self.report.warning(f"Available worksheets: {wb.sheetnames}")
                return None

            # Build a map of merged cell ranges so we can resolve
            # what value a visually merged cell actually holds.
            # In openpyxl, only the top-left cell of a merge holds the value;
            # the rest return None. This map points every cell back to its top-left.
            merge_map = {}
            for merge_range in sheet.merged_cells.ranges:
                top_left_val = sheet.cell(
                    merge_range.min_row, merge_range.min_col
                ).value
                for row in range(merge_range.min_row, merge_range.max_row + 1):
                    for col in range(merge_range.min_col, merge_range.max_col + 1):
                        merge_map[(row, col)] = top_left_val

            def resolved(row, col):
                """Return cell value, resolving merged cells to their top-left value."""
                if (row, col) in merge_map:
                    return merge_map[(row, col)]
                return sheet.cell(row, col).value

            # Scan column A downward from row 2 (skip title in A1)
            # Stop when we hit a blank — last valid row is the one before it
            last_row = None
            for row in range(2, sheet.max_row + 2):  # +2 to catch trailing blank
                val = resolved(row, 1)
                if val is None or str(val).strip() == "":
                    if last_row is not None:
                        break  # first blank after data — we're done
                else:
                    last_row = row

            if last_row is None:
                self.report.warning("No revision entries found in column A.")
                return None

            # Collect the full row of data at last_row
            version_value = resolved(last_row, 1)

            if isinstance(version_value, float) and version_value.is_integer():
                return str(int(version_value))
            return str(version_value)
        except Exception as e:
            self.report.exception(f"{e}")
        finally:
            if wb is not None:
                wb.close()

    def extract_mtl_table(self, mtl_file_path: str) -> pd.DataFrame:
        """
        Returns a data frame from a named excel table in the MTL.
        Will raise an exception if it fails.
        This iteration uses xlwings as the extractor. xlwings opens an instance of
        excel and data runs through the app instance. Slower but directly interacts
        with an active version of excel.
        """
        dataframe = pd.DataFrame()
        excel = None
        workbook = None
        try:
            excel = xl.App(visible=False, add_book=False)
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
            if workbook is not None:
                workbook.close()
            if excel is not None:
                excel.quit()

    def extract_input_csv(
        self,
        file_path: str,
        filter_str: str,
    ) -> pd.DataFrame:
        """
        Returns a data frame from an input csv file.
        The filter string is only used for file naming in this function.
        Will raise an exception if it fails.
        """
        # Read the input csv
        df = pd.DataFrame()
        try:
            self.report.info("Extracting the Input file.")
            df = pd.read_csv(
                file_path,
                # na_values=["None", "none", "NULL", "null", ""],
                na_values=[""],
                keep_default_na=False,
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
                    # na_values=["None", "none", "NULL", "null", ""],
                    keep_default_na=False,
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
                    keep_default_na=False,
                )
                self.report.info("Conversion completed!")
                self.report.info(f"Converted input saved to: {fixed_name}")
                return df
            except Exception as e:
                error_msg = (
                    "Conversion attempt failed. This input file is unable to be"
                    + " properly processed in this format. You can try to correct this error"
                    + " yourself by opening the input CSV in excel and saving to the format:"
                    + " 'UTF-8 CSV'. Please report this error to your WAVE admin."
                )
                self.report.highlight_error("Could not convert bad input data.")
                self.report.critical(error_msg, popup=True)
                return df
        except Exception as e:
            error_msg = (
                f"Input extraction unknown exception. Please report this error.\n{e}"
            )
            self.report.highlight_error("Could not convert bad input data.")
            self.report.critical(error_msg, popup=True)
            return df

    def could_extract(
        self, mtl_dataframe: pd.DataFrame, input_dataframe: pd.DataFrame
    ) -> bool:
        if mtl_dataframe.empty:
            self.report.highlight_titled_error(
                " MTL data could not be extracted. Check your selected MTL table."
            )
            return False
        if input_dataframe.empty:
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
