# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
#
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH

# Test
# from __future__ import annotations

# stdlib
from copy import copy
from pathlib import Path

# third party
import pandas as pd
import openpyxl as xl
from openpyxl.utils import range_boundaries, get_column_letter
from openpyxl.worksheet.table import Table
from openpyxl.worksheet.worksheet import Worksheet
from openpyxl.styles import Font

# local
from src.metadata import MTL_VERSION, AppMetadata
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

    def _apply_template_row_style(
        self,
        ws: Worksheet,
        template_row: int,
        target_row: int,
        min_col: int,
        max_col: int,
    ) -> None:
        """
        Copy a limited set of style attributes from template_row to target_row:
        - borders
        - fill (cell background)
        - font color + font size (keeps other font properties from destination)
        """
        for c in range(min_col, max_col + 1):
            src = ws.cell(row=template_row, column=c)
            dst = ws.cell(row=target_row, column=c)

            # borders + fill
            dst.border = copy(src.border)  # type: ignore
            dst.fill = copy(src.fill)  # type: ignore

            # font: copy just size + color
            src_color = src.font.color
            dst.font = Font(
                name=dst.font.name,
                charset=dst.font.charset,
                family=dst.font.family,
                b=dst.font.b,
                i=dst.font.i,
                strike=dst.font.strike,
                outline=dst.font.outline,
                shadow=dst.font.shadow,
                condense=dst.font.condense,
                extend=dst.font.extend,
                u=dst.font.u,
                vertAlign=dst.font.vertAlign,
                scheme=dst.font.scheme,
                size=src.font.size,
                color=copy(src_color) if src_color is not None else None,
            )

    def rebuild_named_table_in_place(
        self,
        mtl_file_path: str | Path,
        input_dataframe: pd.DataFrame,
        output_path: str | Path | None = None,
        clear_old_area: bool = True,  # clears the old excel table range before writing
    ) -> Path:
        """
        Overwrite an existing Excel Table (openpyxl Table) with df (header + values),
        starting at the table's current top-left cell, then resize table.ref.

        Works even if the table is not at A1.
        """
        mtl_worksheet_name = self.metadata.get_worksheet_name()
        table_id = self.metadata.get_table_id()
        # Sanitize pandas NA values to python for correct data type transfer
        self.report.debug("Sanitizing pd.na values from the DataFrame...")
        df = input_dataframe.astype(object).where(pd.notna(input_dataframe), None)
        df = df.replace(r"^\s*$", None, regex=True)

        self.report.debug("Rebuilding Excel Table...")
        mtl_file_path = Path(mtl_file_path)
        self.report.debug(f"Origin path : {mtl_file_path}")
        output_path = (
            Path(output_path)
            if output_path
            else self.report.file_path / f"21471406_v{MTL_VERSION}_updated.xlsx"
        )
        self.report.debug(f"Output path: {output_path}")

        wb = xl.load_workbook(mtl_file_path)
        ws: Worksheet = wb[mtl_worksheet_name]

        if table_id not in ws.tables:
            raise KeyError(
                f"Table '{table_id}' not found in worksheet '{mtl_worksheet_name}'"
            )
        self.report.debug("Table found...")

        table: Table = ws.tables[table_id]
        self.report.debug("Table Set...")

        if not table.ref:
            raise ValueError(f"Table '{table_id}' has no ref range.")

        # Existing table rectangle (including header row)
        min_col, min_row, max_col, max_row = range_boundaries(table.ref)
        self.report.debug("Existing shape:")
        self.report.debug(f"    Col pos: {min_col}")
        self.report.debug(f"    Col len: {max_col}")
        self.report.debug(f"    Row pos: {min_row}")
        self.report.debug(f"    Row len: {max_row}")

        # Where we will write the new table (top-left of existing table)
        start_row, start_col = min_row, min_col
        self.report.debug("Write shape, start:")
        self.report.debug(f"    start col: {start_col}")
        self.report.debug(f"    start row: {start_row}")

        # Optional: clear the old table block (prevents leftover values if new df is smaller)
        if clear_old_area:
            self.report.debug("Trying to clear area...")
            for r in range(min_row, max_row + 1):  # type: ignore
                for c in range(min_col, max_col + 1):  # type: ignore
                    ws.cell(row=r, column=c).value = None

        # Write header
        self.report.debug("Writing headers...")
        for j, col_name in enumerate(df.columns):
            ws.cell(row=start_row, column=start_col + j).value = str(col_name)  # type: ignore

        # Write data rows
        self.report.debug("Writing rows...")
        for i, row in enumerate(df.itertuples(index=False, name=None), start=1):
            for j, val in enumerate(row):
                ws.cell(row=start_row + i, column=start_col + j).value = val  # type: ignore

        # Resize table ref to match df (header + data)
        # header is at start_row
        new_max_row = start_row + len(df)  # type: ignore
        new_max_col = start_col + df.shape[1] - 1  # type: ignore

        template_row = min(max_row, max(start_row + 1, max_row))  # type: ignore
        for r in range(max_row + 1, new_max_row + 1):  # type: ignore
            self._apply_template_row_style(ws, template_row, r, start_col, new_max_col)  # type: ignore

        new_ref = (
            f"{get_column_letter(start_col)}{start_row}:"  # type: ignore
            f"{get_column_letter(new_max_col)}{new_max_row}"
        )
        table.ref = new_ref

        wb.save(output_path)
        wb.close()
        return output_path
