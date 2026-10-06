# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH
# This tool was created with the help of AI.

# stdlib
import time
from datetime import UTC, datetime
from pathlib import Path

# third party
import pandas as pd
import pywintypes
import xlwings as xl

# local core
from m_wave.core.pdf_reporting import PDFReportStatus
from m_wave.core.reporting import Reporting

# local wave pack
from m_wave.wave_packs.mtl.metadata import Metadata
from m_wave.wave_packs.mtl.pdf_reporting import MTLAppendReportData, UpsertIssue


class DataAppender:
    def __init__(
        self,
        report: Reporting,
        metadata: Metadata,
    ) -> None:
        self.report = report
        self.metadata = metadata

        # Structured outcome of the most recent updert, for the PDF report.
        # Process layer reads this after calling upsert()
        self.issues: list[UpsertIssue] = []
        self.rows_in_mtl_before: int = 0
        self.rows_in_pib: int = 0
        self.rows_in_mtl_after: int = 0
        self.updated_keys: list[str] = []
        self.appeneded_keys: list[str] = []
        self.key_columns: list[str] = []
        self.artifacts: list[tuple[str, str]] = []
        self.filter_action: str | None = None
        self.written_to_mtl: bool = False
        self.mtl_output_name: str | None = None

    def _reset_report_state(self) -> None:
        """Clear the previous run so a second upsert cannot inherit its state."""
        self.issues = []
        self.rows_in_mtl_before = 0
        self.rows_in_pib = 0
        self.rows_in_mtl_after = 0
        self.updated_keys = []
        self.appended_keys = []
        self.key_columns = []
        self.artifacts = []
        self.filter_action = None
        self.written_to_mtl = False
        self.mtl_output_name = None

    def _add_issue(self, check: str, detail: str, severity: str = "error") -> None:
        self.issues.append(UpsertIssue(check=check, detail=detail, severity=severity))

    @staticmethod
    def _key_label(key) -> str:
        """Render a single or composite index value as one readable key."""
        if isinstance(key, tuple):
            return " | ".join(str(part) for part in key)
        return str(key)

    def upsert(
        self,
        mtl_dataframe: pd.DataFrame,
        input_dataframe: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Update and insert an input_dataframe into the mtl_dataframe, matching on
        'keys' (a list of column names, sourced form the MTL config for the current
        table type). The MTL is always treated as the source of truth for the table's
        schema and keys:

            - Column schema: every column in the input must already exist in the
            MTL. If the input contains a column in the MTL does not recognize, the
            upsert is stopped and the user is prompted to check that
            they are using the correct input data.

            - Key integrity: the key columns must be present in the input, and the
            key values must be unique. Duplicate keys found in the input, or already
            present in the MTL, are reported to the user rather than silently merged or
            dropped.

            - XOR append: for every key, the default contains either the updated MTL
            row or a newly appended row, never both, and never a duplicate. This is
            verified defensively after the merge.

        Returns an empty data frame if the upsert cannot be safely completed.
        """

        output = pd.DataFrame()
        self._reset_report_state()
        self.rows_in_mtl_before = len(mtl_dataframe)
        self.rows_in_pib = len(input_dataframe)

        try:
            # keys are defined per table in the mtl config json.
            keys = self.metadata.get_table_index_keys()
            self.key_columns = list(keys)
            original_columns = mtl_dataframe.columns

            unmatched_columns = set(input_dataframe.columns) - set(original_columns)
            if unmatched_columns:
                unmatched_list = ", ".join(sorted(unmatched_columns))
                self._add_issue(
                    "Column Schema",
                    f"PI Builder column(s) not found in the MTL: {unmatched_list}.",
                )
                self.report.highlight_titled_error(
                    f"PI Builder column(s) not found in the MTL: {unmatched_list}",
                    title="PI Builder / MTL COLUMN MISMATCH",
                    is_critical=True,
                )
                self.report.critical(
                    "The upsert was stopped because the PI Builder file contains "
                    f"column(s) that do not exist in the mtl ({unmatched_list}). "
                    "Please confirm that you are using the correct PI Builder file, or "
                    "correct the column headers so they match the MTL exactly, "
                    "then try again.",
                    popup=True,
                )
                return output

            missing_key_columns = set(keys) - set(input_dataframe.columns)
            if missing_key_columns:
                missing_list = ", ".join(sorted(missing_key_columns))
                self._add_issue(
                    "Key Columns",
                    "The PI Builder file is missing the required key column(s): "
                    f"{missing_list}",
                )
                self.report.critical(
                    "The upsert was stopped because the PI Builder file is missing "
                    f"the required key column(s): {missing_list}. These keys "
                    "are defined in the MTL configuration and are required to "
                    "match PI Builder rows to the MTL. Please check that you are "
                    "using the correct PI Builder data.",
                    popup=True,
                )
                return output

            keyed_mtl = mtl_dataframe.set_index(keys)
            keyed_input = input_dataframe.set_index(keys)

            input_dupe_mask = keyed_input.index.duplicated(keep=False)
            if input_dupe_mask.any():
                duplicate_keys = sorted(
                    set(keyed_input.index[input_dupe_mask].tolist())
                )
                self._add_issue(
                    "Key Uniqueness",
                    f"{len(duplicate_keys)} duplicate key value(s) in the PI Builder "
                    f"csv: {', '.join(self._key_label(k) for k in duplicate_keys[:10])}",
                )
                self.report.highlight_titled_error(
                    f"Duiplicate key value(s) found in the PI Builder csv: {duplicate_keys}",
                    title="DUPLICATE KEYS IN PI BUILDER CSV",
                    is_critical=True,
                )
                self.report.critical(
                    "The upsert was stopped because the PI Builder file contains "
                    "more than one row for th same key value. Each key combination "
                    f"({', '.join(keys)}) must be unique. Please remove or "
                    "consolidate the duplicate row(s) listed above in your "
                    "PI Builder data and try again.",
                    popup=True,
                )
                return output

            mtl_dupe_mask = keyed_mtl.index.duplicated(keep=False)
            if mtl_dupe_mask.any():
                duplicate_keys = sorted(set(keyed_mtl.index[mtl_dupe_mask].tolist()))
                self._add_issue(
                    "MTL Key Uniqueness",
                    f"{len(duplicate_keys)} duplicate key value(s) already in the MTL "
                    f"table: {', '.join(self._key_label(k) for k in duplicate_keys[:10])}",
                )
                self.report.critical(
                    "The upsert was stopped because the existing MTL table contains "
                    f"duplicate key value(s): {duplicate_keys}. Please resolve these "
                    "duplicates in the MTL before appending or updating data.",
                    popup=True,
                )
                return output

            # Save each data frame to keep record of the changes.
            mtl_dataframe.to_csv(
                self.report.report_dir / "mtl_dataframe_before.csv", index=False
            )
            self.artifacts.append(
                (
                    "mtl_dataframe_before.csv",
                    "The MTL table as extracted, before any changes.",
                )
            )
            input_dataframe.to_csv(
                self.report.report_dir / "pi_dataframe.csv", index=False
            )
            self.artifacts.append(
                ("pi_dataframe.csv", "The PI Builder rows used as the upsert source.")
            )

            updated_keys = keyed_mtl.index.intersection(keyed_input.index)
            new_keys = keyed_input.index.difference(keyed_mtl.index)
            self.updated_keys = [self._key_label(k) for k in updated_keys]
            self.appended_keys = [self._key_label(k) for k in new_keys]

            remaining_mtl = keyed_mtl[~keyed_mtl.index.isin(keyed_input.index)]
            output = (
                pd.concat([remaining_mtl, keyed_input])
                .reset_index()
                .reindex(columns=original_columns)
            )

            result_keyed = output.set_index(keys)
            if result_keyed.index.duplicated().any():
                self._add_issue(
                    "Result integrity",
                    "The merge would have produced duplicate keys in the resulting "
                    "table. No changes were made.",
                )
                self.report.critical(
                    "The upsert was aborted because it would have produced "
                    "duplicate keys in the resulting table. No changes were "
                    "made. Please report this issue.",
                    popup=True,
                )
                return pd.DataFrame()

            self.rows_in_mtl_after = len(output)
            self.report.info(
                f"Upsert complete: {len(updated_keys)} rows(s) updated, "
                f"{len(new_keys)} row(s) appended."
            )
            return output

        except KeyError as e:
            error_msg = f"A key error occurred during upserting.\n{e}"
            self._add_issue("Key error", error_msg)
            self.report.exception(error_msg)
            return pd.DataFrame()
        except ValueError as e:
            error_msg = f"A value error occurred during upserting.\n{e}"
            self._add_issue("Value error", error_msg)
            self.report.exception(error_msg)
            return pd.DataFrame()
        except Exception as e:
            error_msg = f"An unexpected error occurred during upserting.\n{e}"
            self._add_issue("Unexpected error", error_msg)
            self.report.exception(error_msg)
            return pd.DataFrame()

    def export_to_csv(self, appended_dataframe: pd.DataFrame) -> None:
        """
        Used to export the new appended data frame to csv format.
        """
        appended_filename = "mtl_dataframe_after.csv"
        appended_filepath = self.report.report_dir / appended_filename
        self.report.info(f"Exporting the appended data to:  {appended_filepath}")
        self.report.info("This data is supplied as the complete mtl table.")
        self.report.info("This includes all appended rows, and updated rows,")
        self.report.info("along with the full data within the supplied MTL file.")
        appended_dataframe.to_csv(appended_filepath, encoding="utf-8", index=False)
        self.artifacts.append(
            (appended_filename, "The complete MTL table after the upsert.")
        )

    def _table_has_filter(self, worksheet, table) -> bool:
        """
        Return True if the named table (or the worksheet itself) currently has
        an active AutoFilter applied. A filter hides rows in the table range,
        which makes table.update() write values into the wrong physical rows.
        Uses the COM api because xlwings does not wrap ListObject.AutoFilter.
        """
        try:
            list_object = table.api
            auto_filter = list_object.AutoFilter
            if auto_filter is not None and auto_filter.FilterMode:
                return True
        except Exception as e:
            self.report.exception(
                f"Could not read the table AutoFilter state. {e}", report=False
            )

        try:
            if worksheet.api.AutoFilterMode:
                return True
            if worksheet.api.FitlerMode:
                return True
        except Exception as e:
            self.report.exception(
                f"Could not read the worksheet AutoFilter state. {e}", report=False
            )

        return False

    def _toggle_table_filter(self, worksheet, table) -> bool:
        """
        Attempt to show all rows and remove the AutoFilter from the table and the
        worksheet. Returns True if the filter appears to be gone.
        """
        try:
            table.show_autofilter = not table.show_autofilter
        except Exception as e:
            self.report.exception(f"Xlwings filter clear failed: {e}")

        try:
            auto_filter = table.api.AutoFilter
            if auto_filter is not None and auto_filter.FilterMode:
                table.api.Range.AutoFilter()
        except Exception as e:
            self.report.exception(f"Table level filter clear failed: {e}")

        try:
            if worksheet.api.FilterMode:
                worksheet.api.ShowAllData()
        except Exception as e:
            self.report.exception(f"ShowAllData failed. {e}")

        try:
            if worksheet.api.AutoFilterMode:
                worksheet.api.AutoFilterMode = False
        except Exception as e:
            self.report.exception(f"AutoFilterMode reset failed. {e}")

        return not self._table_has_filter(worksheet, table)

    def _clear_table_filter(self, worksheet, table) -> bool:
        """
        Attempt to show all rows and remove the AutoFilter from the table and the
        worksheet. Returns True if the filter appears to be gone.
        """
        # xlwings attempt first, then try the AIs api attempts
        try:
            auto_filter = table.show_autofilter
            if auto_filter == True:
                table.show_autofilter = False
        except Exception as e:
            self.report.exception(f"Xlwings filter clear failed: {e}")

        try:
            auto_filter = table.api.AutoFilter
            if auto_filter is not None and auto_filter.FilterMode:
                table.api.Range.AutoFilter()
        except Exception as e:
            self.report.exception(f"Table level filter clear failed: {e}")

        try:
            if worksheet.api.FilterMode:
                worksheet.api.ShowAllData()
        except Exception as e:
            self.report.exception(f"ShowAllData failed. {e}")

        try:
            if worksheet.api.AutoFilterMode:
                worksheet.api.AutoFilterMode = False
        except Exception as e:
            self.report.exception(f"AutoFilterMode reset failed. {e}")

        return not self._table_has_filter(worksheet, table)

    def _resolve_filters(self, worksheet, table) -> bool:
        """
        Check the working copy for an active filter before writing to it.

        If a filter is found the user is asked to clear it themselves, becaue a manual
        fix is th eonly way to guarantee a clean write. They may also let the WAVE
        try to clear it automatically, with the cavear thatt the cauto clean can
        still leave artifacts and the process may still fail.

        Returns True when it is safe to continue, False when the process should
        stop so the usre cna fix the MTL by hand.
        """
        if not self._table_has_filter(worksheet, table):
            self.report.info("No active filers found on this table.")
            self.filter_action = "No active filter was found on the table."
            return True

        self.report.highlight_titled_error(
            "Writing to a filtered table can scramble the rows in the appended MTL.",
            title="ACTIVE FILTER DETECTED",
        )

        clean_it = self.report.ask(
            f"An active filter was found on the {worksheet.name} table.\n\n"
            "Filters hide rows, and writing into a filtered table can scramble "
            "the appended data.\n\n"
            "The safest fix is to clear all filters in the MTL yourslef, "
            "save it, and run the append process again.\n\n"
            "The WAVE can also try to clear the filter for you, but the "
            "automatic clean may still produce artifacts. If it does, clear "
            "the filers manually and try again.\n\n"
            "Let the WAVE try to clear the filter now?",
            title="ACTIVE FILTER DETECTED",
            yes_text="Clear it for me",
            no_text="I will fix it myself",
            default=False,
        )

        if not clean_it:
            self.filter_action = (
                "An active filter was found. The user chose to clear it automatically."
            )
            self.report.warning(
                "Append stopped so the filters can be cleared manually. "
                "Remove all filters form the table, dave the MTL, then run "
                "the append process again.",
                popup=True,
            )
            return False
        self.report.info("Attempting to clear the filters automatically...")
        if not self._toggle_table_filter(worksheet, table):
            self.filter_action = (
                "An active filer was found and could not be cleared automatically."
            )
            self.report.critical(
                "The filter could not be cleared automatically. Please remove "
                "all filters form the table in the MTL, save it, and run the "
                "append process agian.",
                popup=True,
            )
            return False
        self.filter_action = "An active filter was cleared automatically."
        self._add_issue(
            "Table filter",
            "A filter was cleared automatically. Rows in the appened workbook "
            "should be reviewed for scrambling.",
            severity="warning",
        )
        self.report.warning(
            "The filter was cleared automatically. Please review the appeneded "
            "file carefully. If the rows look scrambled, clear the filters in "
            "the MTL manually and run the append process again."
        )
        return True

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
            output_file_path = self.report.report_dir / f"{doc_num}_appended.xlsx"

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
                    if e.args[0] == -2146777998 and attempt < retries - 1:  # OLE Busy
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

            self.report.info("Checking the table for active filters...")
            if not self._resolve_filters(worksheet, table):
                self.report.error(
                    "The MTL was not updated. No changes were written.",
                    popup=True,
                )
                return

            table.update(appended_dataframe, index=False)

            self.report.info("Table values updated.")

            # Reapply the autofilter so the MTL is as unchanged as possible
            if not self._toggle_table_filter(worksheet, table):
                self.report.error(
                    "The MTL autofilter could not be reapplied after updating. "
                    "Changes not saved.",
                    popup=True,
                )
                return

            workbook.save()
            self.written_to_mtl = True
            self.artifacts.append(
                (output_file_path.name, "A copy of the MTL with the table replaced.")
            )
            self.report.subtitle(" 🎉 UPDATE/APPEND COMPLETED SUCCESSFULLY 🎉 ")
            self.report.info(
                " 🎉 UPDATE/APPEND COMPLETED SUCCESSFULLY 🎉 ",
                popup=True,
                log=False,
                report=False,
            )

            self.mtl_output_name = output_file_path.name
            self.report.info(f"MTL Saved to a new file at: ../{output_file_path.name}")

        except Exception as e:
            self._add_issue(
                "MTL export",
                "The appended data could not be written to the MTL workbook.",
            )
            self.report.error(
                "Failed to export the data to the MTL. Check the general log and report "
                "to an admin if necessary.",
                popup=True,
            )
            self.report.exception(f"\n{e}")

        finally:
            if workbook is not None:
                workbook.close()
            if excel is not None:
                excel.quit()

    def build_append_report(
        self,
        status: PDFReportStatus,
        mtl_worksheet_name: str,
        mtl_file_path: str,
        input_file_path: str,
        filter_string: str | None = None,
    ) -> MTLAppendReportData:
        """Snapshot the appender's outcome as a PDF report model."""
        appender = self
        return MTLAppendReportData(
            title="MTL Append Report",
            subtitle=f"{self.metadata.get_mtl_doc_num()} / {mtl_worksheet_name}",
            report_id=self.report.report_name,
            user=self.report.user,
            created_date=datetime.now(UTC),
            status=status,
            mtl_source=Path(mtl_file_path),
            pib_source=Path(input_file_path),
            worksheet_name=mtl_worksheet_name,
            filter_string=filter_string,
            rows_in_mtl_before=appender.rows_in_mtl_before,
            rows_in_pib=appender.rows_in_pib,
            rows_in_mtl_after=appender.rows_in_mtl_after,
            rows_updated=len(appender.updated_keys),
            rows_appended=len(appender.appended_keys),
            updated_keys=appender.updated_keys,
            appended_keys=appender.appended_keys,
            issues=appender.issues,
            key_columns=appender.key_columns,
            artifacts=appender.artifacts,
            filter_action=appender.filter_action,
            written_to_mtl=appender.written_to_mtl,
            mtl_output_name=appender.mtl_output_name,
        )
