# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH
# This tool was created with the help of AI.

# stdlib
from pathlib import Path
from typing import Any

# third party
import datacompy
import pandas as pd

from m_wave.core.reporting.pdf_utils import PDFReportStatus

# local core
from m_wave.core.reporting.reporter import Reporter

# local extension
from m_wave.extensions.mtl.function.security import SecurityParser
from m_wave.extensions.mtl.pdf_template import (
    ColumnDifferenceSummary,
    ComparisonRecord,
    ReportIssue,
)
from m_wave.extensions.mtl.utils.metadata import Metadata
from m_wave.extensions.mtl.utils.utils import report_shape_differences


class Comparisons:
    """
    Compares a Master Tag List (MTL) table against a PI Builder input table.

    datacompy owns the comparison. This class only decides what to exclude,
    and how to render what datacompy found. A blank on one side and a value
    on the other is a difference and is always reported.
    """

    def __init__(self, reporter: Reporter, metadata: Metadata) -> None:
        self.reporter = reporter
        self.journal = reporter.journal
        self.notify = reporter.notifier
        self.debug = reporter.debug

        self.metadata = metadata
        self.manual_review_columns = self.metadata.dataframe_formatting[
            "manual_review_columns"
        ]
        self.security_setting_columns = self.metadata.dataframe_formatting[
            "security_setting_columns"
        ]

        self.sec_string_parser = SecurityParser(self.reporter, self.metadata)

        # NOTE: use .clear() to reset list.
        self.comparison_issues: list[ReportIssue] = []
        self.comparison_fields: dict[str, Any] = {}
        self.comparison_export_path: Path = Path()

    @staticmethod
    def _display(value: Any) -> str:
        """Human readable cell value, with blanks made explicit."""
        blank_token = ""
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return blank_token
        if pd.isna(value):
            return blank_token
        text = str(value).strip()
        return text if text else blank_token

    def compare(
        self,
        mtl_dataframe: pd.DataFrame,
        pib_dataframe: pd.DataFrame,
        mtl_source: Path,
        pib_source: Path,
        exclude_manual_columns: bool,
        sort_fn=None,
    ) -> PDFReportStatus:
        """
        Compare the MTL against the PI Builder input. Returns a DataComPy result via
        a PDFReportStatus. Either PASS, FAIL, or ERRORED
        """
        df1_name, df2_name = "MTL", "PI Builder"
        self.mtl_source: Path = mtl_source
        self.pib_source: Path = pib_source
        self.journal.info("Obtaining the table index keys from metadata...")
        key_columns = [c.lower() for c in self.metadata.get_table_index_keys()]

        if mtl_dataframe.empty:
            issue = ReportIssue(
                "Checking MTL dataframe",
                "Checking if the MTL dataframe is empty, and it returned true "
                "stopping the comparison.",
                "error",
            )
            self.comparison_issues.append(issue)
            self.journal.error(
                "There was a problem returning the MTL data. Empty table detected. "
                "Stopping the process."
            )
            return PDFReportStatus.ERRORED

        if pib_dataframe.empty:
            issue = ReportIssue(
                "Checking PI Builder dataframe",
                "Checking if the PI Builder dataframe is empty, and it returned true "
                "stopping the comparison.",
                "error",
            )
            self.comparison_issues.append(issue)
            self.journal.error(
                "There was a problem returning the PI Builder data. "
                "Empty table detected. Stopping the process."
            )
            return PDFReportStatus.ERRORED

        report_shape_differences(self.reporter, mtl_dataframe, pib_dataframe)
        self.journal.heading("Comparing...")

        # Lowercase up front so exclusions and key names line up with the
        # names datacompy uses internally.
        mtl = mtl_dataframe.rename(columns=str.lower)
        inp = pib_dataframe.rename(columns=str.lower)

        # TODO: Push this to the external json config.
        always_excluded = ["Asset Details"]
        ###

        excluded = sorted(
            {c for c in mtl.columns if c in self.manual_review_columns}
            | {c for c in inp.columns if c in self.manual_review_columns}
            | {c for c in always_excluded}
        )

        if excluded and exclude_manual_columns:
            self.journal.warning(
                "The following columns are EXCLUDED from this comparison."
            )
            for column in excluded:
                self.journal.warning(f"\t- {column}")
            self.journal.warning(
                "These columns require a manual check by the reviewer by design. "
                "They are reconfigured for the master tag list, so differences "
                "here are expected and are not defects or artifacts."
            )

            mtl = mtl.drop(columns=excluded, errors="ignore")
            inp = inp.drop(columns=excluded, errors="ignore")

        missing = [
            k for k in key_columns if k not in mtl.columns or k not in inp.columns
        ]
        if missing:
            issue = ReportIssue(
                "Missing Key Columns",
                "While confirming column index keys, one or both tables are missing "
                "columns required for comparison.",
                "error",
            )
            self.comparison_issues.append(issue)
            self.journal.error(
                "Cannot compare. These index key columns are missing from one or "
                f"both tables: {', '.join(missing)}"
            )
            return PDFReportStatus.ERRORED

        # Normalize security strings, if they exist
        found_sec_columns = set(self.security_setting_columns)
        found_sec_columns &= set(mtl.columns)
        found_sec_columns &= set(inp.columns)

        if found_sec_columns:
            self.notify.warning(
                "Security strings were found for this comparison.\n\n"
                "Normalization of the security strings are needed for "
                "proper comparisons. This process does not remove values "
                "but will sort them alphabetically."
            )

        for column in found_sec_columns:
            mtl[column] = mtl[column].map(
                lambda value: self.sec_string_parser.canonicalize_security_string(
                    self._display(value)
                )
            )
            inp[column] = inp[column].map(
                lambda value: self.sec_string_parser.canonicalize_security_string(
                    self._display(value)
                )
            )

        # DataComPy Comparison
        comparison = datacompy.PandasCompare(
            mtl,
            inp,
            join_columns=key_columns,
            df1_name=df1_name,
            df2_name=df2_name,
        )

        # Collecting unmatched record artifacts.
        self.journal.heading("Non matching records are now being recorded.")
        self.journal.info(
            "Any records within the 'mtl_non_matching_records.csv' or "
            "'pi_builder_non_matching_records.csv' file are records that have no "
            "matching comparison record and will require manual fixes."
        )
        self.reporter.artifacts.save_csv(
            "mtl_non_matching_records.csv",
            comparison.df1_unq_rows,
            "MTL/CMD records without a matching PI Builder record to compare to.",
        )
        self.reporter.artifacts.save_csv(
            "pi_builder_non_matching_records.csv",
            comparison.df2_unq_rows,
            "PI Builder records without a matching MTL/CMD record to compare to.",
        )

        if comparison.df1_unq_rows.empty and comparison.df2_unq_rows.empty:
            self.journal.heading(" ✓ No non matching records were found!")

        if not comparison.df1_unq_rows.empty:
            self.journal.warning(
                f"{len(comparison.df1_unq_rows)} record(s) exist only in the "
                f"{df1_name}. See mtl_non_matching_records.csv."
            )
        if not comparison.df2_unq_rows.empty:
            self.journal.warning(
                f"{len(comparison.df2_unq_rows)} record(s) exist only in the "
                f"{df2_name}. See pi_builder_non_matching_records.csv."
            )

        # Compare matching records
        self.journal.heading("Matching records will now be compared.")

        # datacompy flags every compared column with a <col>_match boolean on
        # intersect_rows, and treats blank vs value as a mismatch. Trust it.
        #
        # Derive the compared columns from intersect_rows itself rather than
        # from column_stats, whose element type varies between datacompy
        # versions (dict in some, dataclass in others).
        intersect = comparison.intersect_rows
        suffix_1, suffix_2 = f"_{df1_name}", f"_{df2_name}"

        compared = [
            column[: -len("_match")]
            for column in intersect.columns
            if column.endswith("_match")
            and f"{column[: -len('_match')]}{suffix_1}" in intersect.columns
            and f"{column[: -len('_match')]}{suffix_2}" in intersect.columns
        ]
        if not compared:
            issue = ReportIssue(
                "No Matching Records",
                "Could not locate any matching value pairs on "
                f"intersecting rows using suffixes {suffix_1!r} and {suffix_2!r}.",
                "error",
            )
            self.comparison_issues.append(issue)
            self.journal.error(
                "Could not locate any <column>_match / value pairs on "
                f"intersect_rows using suffixes {suffix_1!r} and {suffix_2!r}. "
                f"Columns present: {list(intersect.columns)}"
            )
            return PDFReportStatus.ERRORED

        long_rows: list[dict[str, Any]] = []
        sec_rows: list[dict[str, str]] = []
        for column in compared:
            differing = intersect.loc[~intersect[f"{column}_match"].astype(bool)]
            for position in differing.index:
                record = {k: intersect.at[position, k] for k in key_columns}
                record["column"] = column
                record[df1_name] = self._display(
                    intersect.at[position, f"{column}{suffix_1}"]
                )
                record[df2_name] = self._display(
                    intersect.at[position, f"{column}{suffix_2}"]
                )
                long_rows.append(record)
                if column in self.security_setting_columns:
                    sec_rows.append(record)

        long_form_comparison = pd.DataFrame(
            long_rows, columns=[*key_columns, "column", df1_name, df2_name]
        )
        sec_records: pd.DataFrame = pd.DataFrame(
            sec_rows, columns=[*key_columns, "column", df1_name, df2_name]
        )

        name_column = "name" if "name" in sec_records.columns else None

        self.debug.debug("security sting columns: %s", self.security_setting_columns)
        for row in sec_records.to_dict(orient="records"):
            if name_column is not None:
                record_name = self._display(row[name_column])
            else:
                record_name = ", ".join(
                    f"{key}={self._display(row[key])}" for key in key_columns
                )
            result = self.sec_string_parser.compare_security_strings(
                record_name, row["column"], row[df1_name], row[df2_name]
            )

            self.debug.debug("security string comparison: %s", str(result))

        self.comparison_export_path = self.reporter.artifacts.save_csv(
            "comparison_by_column.csv",
            long_form_comparison,
            "A comparison file that displays the comparison differences "
            "over a single column.",
        )

        self.reporter.artifacts.save_csv(
            "comparison_by_record.csv",
            comparison.all_mismatch(ignore_matching_cols=True),
            "A comparison file that displays the comparison differences "
            "over a complete record. (May contain blank values for columns "
            "that do not affect a particular record.)",
        )

        matches = comparison.matches()

        if not long_form_comparison.empty:
            self.journal.error_banner("COMPARISON FAILED")
            self.notify.error(" ⛔ COMPARISON FAILED ⛔ ", "Comparison Failed")
            self.journal.info(
                f"{len(long_form_comparison)} differing cell(s). Reporting the "
                "differences below:"
            )
            key_width = max(len(k) for k in key_columns)
            name_width = max(len(df1_name), len(df2_name))

            for number, (keys, group) in enumerate(
                long_form_comparison.groupby(key_columns, dropna=False, sort=False),
                start=1,
            ):
                print(f"long_form len: {len(long_form_comparison)}")
                if len(long_form_comparison) > 256:
                    self.journal.warning("There are more than 256 errors.")
                    self.journal.warning("Verbose logging forcefully stopped.")
                    self.journal.warning(
                        "Review the generated comparison files for a full review of the data."
                    )
                    break

                keys = keys if isinstance(keys, tuple) else (keys,)
                self.journal.divider()
                self.journal.error(f"Record {number}:")
                for key, value in zip(key_columns, keys):
                    self.journal.error(f"  {key:>{key_width}}: {self._display(value)}")

                for _, row in group.iterrows():
                    self.journal.error("!!!")
                    self.journal.error(f"{'Column':>{key_width}}: {row['column']}")
                    self.journal.error(f"    {df1_name:>{name_width}}: {row[df1_name]}")
                    self.journal.error(f"    {df2_name:>{name_width}}: {row[df2_name]}")

            self.journal.divider()
            self.journal.error("Differences by column:")
            counts = long_form_comparison["column"].value_counts()
            width = max(len(str(c)) for c in counts.index)
            for column, count in counts.items():
                self.journal.error(f"  {column!s:>{width}}: {count}")

            self.comparison_fields = self._build_comparison_fields(
                long_form_comparison, comparison, key_columns, df1_name, df2_name
            )

            return PDFReportStatus.FAIL

        elif not matches:
            self.pdf_report_status = PDFReportStatus.ERRORED
            self.journal.error_banner("COMPARISON COMPLETED WITH PROBLEM RECORDS")
            self.notify.warning(" ⚠️ COMPARISON COMPLETED WITH PROBLEM RECORDS ⚠️ ")
            self.journal.warning(
                "Every compared cell matched, but DataComPy still reports a "
                "mismatch. Unmatched records or column set differences remain. "
                "Please review all generated data files."
            )
            self.journal.info("Full DataComPy report")
            for line in comparison.report().splitlines():
                self.journal.error(line)

            self.comparison_fields = self._build_comparison_fields(
                long_form_comparison, comparison, key_columns, df1_name, df2_name
            )

            return PDFReportStatus.ERRORED

        else:
            self.journal.subtitle("COMPARISON IS SOUND")
            self.notify.info(" 🎉 COMPARISON IS SOUND 🎉 ", "Good news!")
            self.journal.info(
                "Note: Because the comparison is sound, all comparison files "
                "will return blank."
            )

        self.comparison_fields = self._build_comparison_fields(
            long_form_comparison, comparison, key_columns, df1_name, df2_name
        )

        return PDFReportStatus.PASS

    def _build_comparison_fields(
        self,
        long_form: pd.DataFrame,
        comparison: "datacompy.PandasCompare",
        key_columns: list[str],
        df1_name: str,
        df2_name: str,
    ) -> dict[str, Any]:
        """
        Translate the finished comparison into the values MTLReportData needs.

        Nothing here re-compares anything. It only counts and reshapes what
        DataComPy and ``long_form`` already established.
        """
        # A record is a joined key pair. Records that joined are the ones we
        # were actually able to compare.
        records_compared = len(comparison.intersect_rows)

        # A record present on one side only. This is NOT the same as a blank
        # cell inside a record that joined fine.
        missing_from_mtl = len(comparison.df2_unq_rows)
        missing_from_pib = len(comparison.df1_unq_rows)

        column_summaries: list[ColumnDifferenceSummary] = []
        difference_samples: list[ComparisonRecord] = []

        if long_form.empty:
            return {
                "records_compared": records_compared,
                "matching_records": records_compared,
                "non_matching_records": 0,
                "missing_from_mtl": missing_from_mtl,
                "missing_from_pib": missing_from_pib,
                "column_summaries": column_summaries,
                "difference_samples": difference_samples,
            }

        # long_form holds one row per differing cell, so several rows can
        # belong to the same record. The report counts records, not cells.
        non_matching_records = len(long_form[key_columns].drop_duplicates())

        for column, group in long_form.groupby("column", sort=False):
            column_summaries.append(
                ColumnDifferenceSummary(
                    column=str(column),
                    difference_count=len(group),
                    missing_from_mtl=int(
                        (group[df1_name].map(self._display) == "").sum()
                    ),
                    missing_from_pib=int(
                        (group[df2_name].map(self._display) == "").sum()
                    ),
                )
            )

        # Worst offenders first, so the reader sees the real problem on page one.
        column_summaries.sort(key=lambda s: (-s.difference_count, s.column))

        for _, row in long_form.iterrows():
            mtl_text = self._display(row[df1_name])
            pib_text = self._display(row[df2_name])
            one_side_blank = not mtl_text or not pib_text

            difference_samples.append(
                ComparisonRecord(
                    record_key=" | ".join(
                        self._display(row[key]) for key in key_columns
                    ),
                    column=str(row["column"]),
                    # None renders as an em dash in the PDF, which reads better
                    # than an empty cell the reader might mistake for a bug.
                    mtl_value=mtl_text or None,
                    pib_value=pib_text or None,
                    severity="warning" if one_side_blank else "error",
                )
            )

        return {
            "records_compared": records_compared,
            "matching_records": records_compared - non_matching_records,
            "non_matching_records": non_matching_records,
            "missing_from_mtl": missing_from_mtl,
            "missing_from_pib": missing_from_pib,
            "column_summaries": column_summaries,
            "difference_samples": difference_samples,
        }
