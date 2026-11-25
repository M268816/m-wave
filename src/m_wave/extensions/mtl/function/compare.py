# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH
# This tool was created with the help of AI.

# stdlib
from collections.abc import Callable
from dataclasses import dataclass, field
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
    SecurityComparisonSummary,
    SecurityDifferenceRecord,
)
from m_wave.extensions.mtl.utils.metadata import Metadata
from m_wave.extensions.mtl.utils.utils import report_shape_differences

MTL_NAME = "MTL"
PIB_NAME = "PI Builder"
MTL_SUFFIX = f"_{MTL_NAME}"
PIB_SUFFIX = f"_{PIB_NAME}"

# Per record journal output is truncated to this value and the reviewer is directed
# to the generated CSV artifacts instead.
VERBOSE_DIFFERENCE_LIMIT = 256


class _ComparisonAbort(Exception):
    """
    Internal signal: a phase could not continue the run is ERRORED.
    """

    def __init__(self, title: str, detail: str, journal_message: str) -> None:
        super().__init__(journal_message)
        self.title = title
        self.detail = detail
        self.journal_message = journal_message


@dataclass
class _PreparedFrames:
    """
    Frames ready for comparison, with security columns split out.
    """

    key_columns: list[str]
    mtl: pd.DataFrame
    pib: pd.DataFrame
    security_columns: list[str] = field(default_factory=list)
    mtl_security: pd.DataFrame = field(default_factory=pd.DataFrame)
    pib_security: pd.DataFrame = field(default_factory=pd.DataFrame)


@dataclass
class SecurityComparisonResult:
    """
    Outcome of the security-string phase, independent of the DataComPy result.

    ``mtl_matches_pib``: every compared MTL string matches its PI Builder string.
    ``pib_matches_matrix``: every PI Builder string satisfied the security matrix.
    ``errored``: at lest one string could not be evaluated, so the result is incomplete.
    """

    performed: bool = False
    strings_compared: int = 0
    mtl_matches_pib: bool = True
    pib_matches_matrix: bool = True
    errored: bool = False
    results: list[dict[str, Any]] = field(default_factory=list)
    records: pd.DataFrame = field(default_factory=pd.DataFrame)
    records_compared: set[str] = field(default_factory=set)
    failing_records: set[str] = field(default_factory=set)
    mtl_pib_mismatches: int = 0
    matrix_failures: int = 0
    unevaluated_strings: int = 0

    @property
    def failed(self) -> bool:
        """
        A definite security failure was found.
        """
        return self.performed and not (self.mtl_matches_pib and self.pib_matches_matrix)

    @property
    def passed(self) -> bool:
        """
        A definite pass.
        """
        return not self.errored and not self.failed


class Comparisons:
    """
    Compares a Master Tag List (MTL) table against a PI Builder input table.

    DataComPy owns the cell for cell comparison of ordinary columns. Security string
    columns are handled in one of two modes.

    ``Parsed`` (default): security columns are removed before DataCompPy runs and
        evaluated separately by ``SecurityParser``, because equivalent security
        strings are not necessarily identical text and must also be checked against the
        security matrix
    ``Not Parsed``: the security string columns are removed form the comparison entirely
    and left for the reviewer to check by hand. Useful for development and for
    side by side checks of the parser results.

    Always excluded columns are removed from both modes. A blank value on one side
    of the comparison and a value on the other is a difference and is always reported.
    """

    def __init__(self, reporter: Reporter, metadata: Metadata) -> None:
        self.reporter = reporter
        self.journal = reporter.journal
        self.notify = reporter.notifier
        self.debug = reporter.debug

        self.metadata = metadata
        self.sec_string_parser = SecurityParser(self.reporter, self.metadata)

        # per run results. reset at the start of every compare() call.
        self.comparison_issues: list[ReportIssue] = []
        self.comparison_fields: dict[str, Any] = {}
        self.comparison_export_path: Path = Path()
        self.security_comparison: SecurityComparisonResult = SecurityComparisonResult()
        self.mtl_source: Path = Path()
        self.pib_source: Path = Path()

    def compare(
        self,
        mtl_dataframe: pd.DataFrame,
        pib_dataframe: pd.DataFrame,
        mtl_source: Path,
        pib_source: Path,
        parse_security_strings: bool,
        sort_fn: Callable | None = None,
    ) -> PDFReportStatus:
        """
        Compare the MTL against the PI Builder input.

        Phases:
            1. Validate inputs.
            2. Prepare frames: normalize names, split out security columns
            3. DataCompPy comparison of non-security columns.
            4. Record unmatched records.
            5. Build cell-level differences.
            6. Security string comparison (MTL vs PI Builder vs security matrix),
                when parsing is enabled.
            7. Save artifacts.
            8. Determine and report the overall status.

        Returns PASS, FAIL, or ERRORED (PDFReportStatus)
        """
        self._reset_run(mtl_source, pib_source)

        try:
            self._validate_inputs(mtl_dataframe, pib_dataframe)
            frames = self._prepare_frames(
                mtl_dataframe, pib_dataframe, parse_security_strings
            )
            comparison = self._run_datacompy(frames)
            self._record_unmatched_records(comparison)
            compared_columns = self._find_compared_columns(comparison)
            long_form = self._build_long_form(
                comparison, compared_columns, frames.key_columns
            )
        except _ComparisonAbort as abt:
            self._record_abort(abt)
            return PDFReportStatus.ERRORED

        self.security_comparison = self._compare_security_strings(
            frames, parse_security_strings
        )
        self._save_comparison_artifacts(comparison, long_form, self.security_comparison)

        status = self._determine_status(comparison, long_form, self.security_comparison)

        self._report_outcome(
            status, comparison, long_form, self.security_comparison, frames.key_columns
        )

        self.comparison_fields = self._build_comparison_fields(
            long_form, comparison, frames.key_columns, MTL_NAME, PIB_NAME
        )

        self.comparison_fields["security"] = self._build_security_summary(
            self.security_comparison, frames, parse_security_strings
        )

        return status

    def _reset_run(self, mtl_source: Path, pib_source: Path) -> None:
        """
        Reset for a new process run.
        """
        self.mtl_source = mtl_source
        self.pib_source = pib_source
        self.comparison_issues.clear()
        self.comparison_fields = {}
        self.comparison_export_path = Path()
        self.security_comparison = SecurityComparisonResult()
        self.sec_string_parser.report_issues.clear()

    def _record_abort(self, abort: _ComparisonAbort) -> None:
        """
        Record a comparison abort through report issues and a journal error.
        """
        self.comparison_issues.append(ReportIssue(abort.title, abort.detail, "error"))
        self.journal.error(abort.journal_message)

    def _validate_inputs(
        self, mtl_dataframe: pd.DataFrame, pib_dataframe: pd.DataFrame
    ) -> None:
        """
        Validate the data frame inputs and journal if there is a problem.
        """
        for frame, label in ((mtl_dataframe, MTL_NAME), (pib_dataframe, PIB_NAME)):
            if frame.empty:
                raise _ComparisonAbort(
                    f"Checking {label} dataframe",
                    f"Checking if the {label} dataframe is empty, and it returned "
                    "true stopping the comparison.",
                    f"There was a problem returning the {label} data. "
                    "Empty table detected. Stopping the process.",
                )

        report_shape_differences(self.reporter, mtl_dataframe, pib_dataframe)
        self.journal.info("✅ Initial comparison checks completed.")

    def _prepare_frames(
        self,
        mtl_dataframe: pd.DataFrame,
        pib_dataframe: pd.DataFrame,
        parse_security_strings: bool,
    ) -> _PreparedFrames:
        """
        Returns prepared data frames for all possible comparisons that may be needed.
        """
        self.journal.info("Obtaining the table index keys from metadata...")
        key_columns = [col.lower() for col in self.metadata.get_table_index_keys()]

        # Lowercase columns up front so exclusions and key names line up with the names
        # DataComPy uses internally.
        mtl = mtl_dataframe.rename(columns=str.lower)
        pib = pib_dataframe.rename(columns=str.lower)

        self._validate_key_columns(mtl, pib, key_columns)

        if parse_security_strings:
            # Security string columns move to the security phase;
            # non-excluded columns go to DataComPy
            frames = self._split_security_columns(mtl, pib, key_columns)
        else:
            mtl, pib = self._remove_security_string_columns(mtl, pib, key_columns)
            frames = _PreparedFrames(key_columns=key_columns, mtl=mtl, pib=pib)

        frames.mtl, frames.pib = self._remove_always_excluded_columns(
            frames.mtl, frames.pib, key_columns
        )

        return frames

    @staticmethod
    def _validate_key_columns(
        mtl: pd.DataFrame, pib: pd.DataFrame, key_columns: list[str]
    ) -> None:
        missing = [
            key
            for key in key_columns
            if key not in mtl.columns or key not in pib.columns
        ]
        if missing:
            raise _ComparisonAbort(
                "Missing Key Columns",
                "While Confirming column index keys, one or both tables are "
                "missing columns required for comparison.",
                "Cannot compare. These index key columns are missing form one or "
                f"both tables: {','.join(missing)}",
            )

    def _split_security_columns(
        self,
        mtl: pd.DataFrame,
        pib: pd.DataFrame,
        key_columns: list[str],
    ) -> _PreparedFrames:
        """
        Move security columns present in both tables into separate key-aligned frames.
        A security column present on only one side stays in the main frames, so
        DataComPy reports the column-set difference.
        """
        configured = [col.lower() for col in self.metadata.security_string_columns]
        shared = [
            col for col in configured if col in mtl.columns and col in pib.columns
        ]

        if not shared:
            return _PreparedFrames(key_columns=key_columns, mtl=mtl, pib=pib)

        return _PreparedFrames(
            key_columns=key_columns,
            mtl=mtl.drop(columns=shared),
            pib=pib.drop(columns=shared),
            security_columns=shared,
            mtl_security=mtl[[*key_columns, *shared]].copy(),
            pib_security=pib[[*key_columns, *shared]].copy(),
        )

    def _remove_always_excluded_columns(
        self, mtl: pd.DataFrame, pib: pd.DataFrame, key_columns: list[str]
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Remove columns configured to be excluded from every comparison.
        """
        return self._drop_columns(
            mtl,
            pib,
            key_columns,
            self.metadata.excluded_columns,
            "The following columns are ALWAYS EXCLUDED from comparisons. "
            "These columns are not compared by design.",
        )

    def _remove_security_string_columns(
        self, mtl: pd.DataFrame, pib: pd.DataFrame, key_columns: list[str]
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Remove security string columns for manual review when parsing is off.
        """
        return self._drop_columns(
            mtl,
            pib,
            key_columns,
            self.metadata.security_string_columns,
            "Security string parsing is OFF. The following security string "
            "columns are EXCLUDED from this comparison and must be reviewed "
            "manually.",
        )

    def _drop_columns(
        self,
        mtl: pd.DataFrame,
        pib: pd.DataFrame,
        key_columns: list[str],
        configured_columns: list[str],
        message: str,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Drop configured columns present in either frame, never a join key.
        """
        configured = {col.lower() for col in configured_columns}
        present = sorted(
            (configured & (set(mtl.columns) | set(pib.columns))) - set(key_columns)
        )
        if not present:
            return mtl, pib

        self.journal.warning(message)
        for column in present:
            self.journal.warning(f"\t- {column}")

        return (
            mtl.drop(columns=present, errors="ignore"),
            pib.drop(columns=present, errors="ignore"),
        )

    @staticmethod
    def _run_datacompy(frames: _PreparedFrames) -> "datacompy.PandasCompare":
        try:
            return datacompy.PandasCompare(
                frames.mtl,
                frames.pib,
                join_columns=frames.key_columns,
                df1_name=MTL_NAME,
                df2_name=PIB_NAME,
            )
        except Exception as e:
            raise _ComparisonAbort(
                "DataComPy Comparison",
                "DataComPy could not compare the MTL and PI Builder Tables.",
                f"DataComPy could not compare the tables: {e}",
            ) from e

    def _record_unmatched_records(self, comparison: "datacompy.PandasCompare") -> None:
        self.journal.heading("Non matching records shall be reported.")
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
            self.journal.heading("✅ No non-matching records were found!")
            return

        if not comparison.df1_unq_rows.empty:
            self.journal.warning(
                f"{len(comparison.df1_unq_rows)} record(s) exist only in the "
                f"{MTL_NAME}. See mtl_non_matching_records.csv"
            )

        if not comparison.df2_unq_rows.empty:
            self.journal.warning(
                f"{len(comparison.df2_unq_rows)} record(s) exist only in the "
                f"{PIB_NAME}. See pi_builder_non_matching_records.csv"
            )

    def _find_compared_columns(
        self,
        comparison: "datacompy.PandasCompare",
    ) -> list[str]:
        """
        Derive compared columns form intersect_rows, which DataComPy marks with a
        <column>_match flag. column_stats is avoided because its element type varies
        between DataComPy versions.
        """
        self.journal.heading("Checking record values for possible comparison pairs.")
        intersect = comparison.intersect_rows
        match_suffix = "_match"

        compared = [
            column[: -len(match_suffix)]
            for column in intersect.columns
            if column.endswith(match_suffix)
            and f"{column[: -len(match_suffix)]}{MTL_SUFFIX}" in intersect.columns
            and f"{column[: -len(match_suffix)]}{PIB_SUFFIX}" in intersect.columns
        ]

        if not compared:
            self.journal.error_banner("COULD NOT LOCATE MATCHING VALUE PAIRS")
            raise _ComparisonAbort(
                "No Matching Records",
                "Could not locate any matching value pairs on intersecting rows "
                f"using suffixes {MTL_SUFFIX!r} and {PIB_SUFFIX!r}.",
                "Could not locate any <column>_match / value pairs on "
                f"intersect_rows using suffixes {MTL_SUFFIX!r} and {PIB_SUFFIX!r}. "
                f"Columns present: {list(intersect.columns)}",
            )

        self.journal.info("✅ All values can be compared.")
        return compared

    def _build_long_form(
        self,
        comparison: "datacompy.PandasCompare",
        compared_columns: list[str],
        key_columns: list[str],
    ) -> pd.DataFrame:
        """
        One row per differing cell on records present in both tables.
        """
        self.journal.heading("Creating a symmetrical comparison data set.")
        intersect = comparison.intersect_rows
        rows: list[dict[str, Any]] = []

        for column in compared_columns:
            # NOTE: "~" is a pandas bitwise not operator
            differing = intersect.loc[~intersect[f"{column}_match"].astype(bool)]
            for position in differing.index:
                record = {key: intersect.at[position, key] for key in key_columns}
                record["column"] = column
                record[MTL_NAME] = self._display(
                    intersect.at[position, f"{column}{MTL_SUFFIX}"]
                )
                record[PIB_NAME] = self._display(
                    intersect.at[position, f"{column}{PIB_SUFFIX}"]
                )
                rows.append(record)

        return pd.DataFrame(rows, columns=[*key_columns, "column", MTL_NAME, PIB_NAME])

    def _compare_security_strings(
        self, frames: _PreparedFrames, parse_security_strings: bool
    ) -> SecurityComparisonResult:
        """
        Compare security strings for records present in both tables.

        Records present on ony one side are already reported by DataComPy as unmatched
        records, so they are not repeated here.
        """
        self.journal.heading("Parsing security string columns")
        if not parse_security_strings:
            self.journal.warning(
                "Security string parsing is turned off for this comparison. "
                "Security string columns were excluded and require manual review."
            )
            return SecurityComparisonResult()

        if not frames.security_columns:
            self.journal.info("✅ No security string columns need comparison.")
            return SecurityComparisonResult()

        self.journal.warning(
            "Security strings were found for this comparison. They are compared by "
            "principal and permission, in canonical PI order, rather than as "
            "literal text, and the PI Builder values are validated against the "
            "security matrix. Malformed security strings and unknown values will "
            "cause this comparison to error."
        )

        result = SecurityComparisonResult(performed=True)
        paired = self._pair_security_records(frames, result)

        if paired is not None:
            for row in paired.to_dict(orient="records"):
                record_name = self._record_name(row, frames.key_columns)
                record_key = " | ".join(
                    self._display(row[key]) for key in frames.key_columns
                )
                for column in frames.security_columns:
                    self._compare_security_cell(
                        row, record_name, record_key, column, result
                    )

            result.records = self._build_security_records(result)

        self._log_security_summary(result)
        self._collect_parser_issues()
        return result

    def _pair_security_records(
        self, frames: _PreparedFrames, result: SecurityComparisonResult
    ) -> pd.DataFrame | None:
        """
        Join the MTL and PI Builder security frames on the table index keys.
        """
        try:
            return frames.mtl_security.merge(
                frames.pib_security,
                on=frames.key_columns,
                how="inner",
                suffixes=(MTL_SUFFIX, PIB_SUFFIX),
                validate="one_to_one",
            )
        except (pd.errors.MergeError, ValueError, TypeError) as e:
            result.errored = True
            message = (
                "Security strings could not be paired by the table index keys. "
                "Duplicate or incompatible key values may be present."
            )
            self.comparison_issues.append(
                ReportIssue("Pairing Security Strings", message, "error")
            )
            self.journal.error(message)
            self.debug.error("Security strings pairing failed: %s", e, error=e)
            return None

    def _compare_security_cell(
        self,
        row: dict[str, Any],
        record_name: str,
        record_key: str,
        column: str,
        result: SecurityComparisonResult,
    ) -> None:
        mtl_value = self._display(row[f"{column}{MTL_SUFFIX}"])
        pib_value = self._display(row[f"{column}{PIB_SUFFIX}"])

        if not mtl_value and not pib_value:
            return

        comparison = self.sec_string_parser.compare_security_strings(
            record_name, column, mtl_value, pib_value
        )

        self.debug.debug("security string comparison: %s", comparison)
        result.strings_compared += 1
        result.records_compared.add(record_key)

        # SecurityParser returns an empty dict when it cannot evaluate a string.
        if not comparison:
            result.errored = True
            result.unevaluated_strings += 1
            return

        result.results.append(comparison)
        string_failed = False

        if not comparison.get("mtl_matches_pi", False):
            result.mtl_matches_pib = False
            result.mtl_pib_mismatches += 1
            string_failed = True

        if not comparison.get("pi_matches_matrix", False):
            result.pib_matches_matrix = False
            result.matrix_failures += 1
            string_failed = True

        if string_failed:
            result.failing_records.add(record_key)

    def _passes_security_matrix(self, comparison: dict[str, Any]) -> bool:
        """
        Whether the PI Builder string satisfies the security matrix.

        Uses SecurityParser's validated value when provided; otherwise it applies the
        same rule from the returned settings.
        """
        if "validated" in comparison:
            return bool(comparison["validated"])

        if self.metadata.worksheet_has_permeable_permissions():
            settings = comparison.get("permeable_settings", {})
            pib_key = "pib_setting_effective"
        else:
            settings = comparison.get("all_settings", {})
            pib_key = "pib_setting"

        return all(
            setting[pib_key] == setting["matrix_setting"]
            for setting in settings.values()
        )

    def _build_security_records(self, result: SecurityComparisonResult) -> pd.DataFrame:
        records = self.sec_string_parser.create_security_dataframe(result.results)
        if records is None:
            result.errored = True
            return pd.DataFrame()
        return records

    def _log_security_summary(self, result: SecurityComparisonResult) -> None:
        if result.strings_compared == 0 and not result.errored:
            self.journal.info("✅ No security strings need comparisons.")
            return

        self.journal.info(f"Security strings compared: {result.strings_compared}")
        if result.errored:
            self.journal.error(
                "⛔ One or more security strings could not be evaluated."
            )
        if not result.mtl_matches_pib:
            self.journal.error("⛔ MTL/CMD security strings do not match PI Builder.")
        if not result.pib_matches_matrix:
            self.journal.error(
                "⛔ PI Builder security strings do not satisfy the security matrix."
            )
        if result.passed:
            self.journal.info(
                "✅ Security strings match and satisfy the security matrix."
            )

    def _collect_parser_issues(self) -> None:
        self.comparison_issues.extend(self.sec_string_parser.report_issues)
        self.sec_string_parser.report_issues.clear()

    def _save_comparison_artifacts(
        self,
        comparison: "datacompy.PandasCompare",
        long_form: pd.DataFrame,
        security: SecurityComparisonResult,
    ) -> None:
        if security.performed:
            self.reporter.artifacts.save_csv(
                "compared_security_strings.csv",
                security.records,
                "A table of compared security strings. Reports differences and "
                "missing values.",
            )

        self.comparison_export_path = self.reporter.artifacts.save_csv(
            "comparison_by_column.csv",
            long_form,
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

    @staticmethod
    def _determine_status(
        comparison: "datacompy.PandasCompare",
        long_form: pd.DataFrame,
        security: SecurityComparisonResult,
    ) -> PDFReportStatus:
        """
        FAIL when any definite difference is found, ERRORED when the result is
        incomplete or DataComPy still reports a mismatch, otherwise PASS.
        """
        if not long_form.empty or security.failed:
            return PDFReportStatus.FAIL
        if security.errored or not comparison.matches():
            return PDFReportStatus.ERRORED
        return PDFReportStatus.PASS

    def _report_outcome(
        self,
        status: PDFReportStatus,
        comparison: "datacompy.PandasCompare",
        long_form: pd.DataFrame,
        security: SecurityComparisonResult,
        key_columns: list[str],
    ) -> None:
        if status == PDFReportStatus.FAIL:
            self._report_failure(long_form, security, key_columns)
        elif status == PDFReportStatus.ERRORED:
            self._report_errored(comparison, security)
        else:
            self._report_pass()

    def _report_failure(
        self,
        long_form: pd.DataFrame,
        security: SecurityComparisonResult,
        key_columns: list[str],
    ) -> None:
        self.journal.error_banner("COMPARISON FAILED")
        self.notify.error("⛔ COMPARISON FAILED ⛔", "Comparison Failed")
        if not long_form.empty:
            self._log_value_differences(long_form, key_columns)
        if security.failed:
            self.journal.error(
                "Security string differences were found. "
                "See 'compared_security_strings.csv' for more details."
            )

    def _report_errored(
        self,
        comparison: "datacompy.PandasCompare",
        security: SecurityComparisonResult,
    ) -> None:
        self.journal.error_banner("COMPARISON COMPLETED WITH PROBLEM RECORDS")
        self.notify.warning("⚠️ COMPARISON COMPLETED WITH PROBLEMS RECORDS ⚠️")

        if security.errored:
            self.journal.warning(
                "One or more security strings could not be evaluated, so the "
                "security comparison is incomplete."
            )

        if not comparison.matches():
            self.journal.warning(
                "Every record available for comparison matches, but DataComPy "
                "still reports a mismatch. Unmatched records or column set "
                "differences remain. Please review all generated data files. "
                "Additionally, the DataComPy report will be generated for review "
                "within the 'journal.log'."
            )
            self.journal.info("Full DataComPy report:")
            for line in comparison.report().splitlines():
                self.journal.error(line)

    def _report_pass(self) -> None:
        self.journal.subtitle("COMPARISON IS SOUND")
        self.notify.info("🎉 COMPARISON IS SOUND 🎉", "Good news!")
        self.journal.info(
            "Note: Because the comparison is sound, all comparison files "
            "will return blank."
        )

    def _log_value_differences(
        self, long_form: pd.DataFrame, key_columns: list[str]
    ) -> None:
        self.journal.info(
            f"{len(long_form)} differing cell(s). Reporting differences below:"
        )

        if len(long_form) > VERBOSE_DIFFERENCE_LIMIT:
            self.journal.warning(
                f"There are more than {VERBOSE_DIFFERENCE_LIMIT} differences."
            )
            self.journal.warning("Verbose logging forcefully stopped.")
            self.journal.warning(
                "Review the generated comparison files for a full review of the data."
            )
        else:
            self._log_difference_records(long_form, key_columns)

        self.journal.divider()
        self.journal.error("Differences by column:")
        counts = long_form["column"].value_counts()
        width = max(len(str(col)) for col in counts.index)
        for column, count in counts.items():
            self.journal.error(f"  {column!s:>{width}}: {count}")

    def _log_difference_records(
        self, long_form: pd.DataFrame, key_columns: list[str]
    ) -> None:
        key_width = max(len(key) for key in key_columns)
        name_width = max(len(MTL_NAME), len(PIB_NAME))

        groups = long_form.groupby(key_columns, dropna=False, sort=False)
        for number, (keys, group) in enumerate(groups, start=1):
            keys = keys if isinstance(keys, tuple) else (keys,)
            self.journal.divider()
            self.journal.error(f"Record {number}:")
            for key, value in zip(key_columns, keys):
                self.journal.error(f"  {key:>{key_width}}: {self._display(value)}")

            for _, row in group.iterrows():
                # TODO: Add an error divider instead of using this
                self.journal.error("!!!")
                ###
                self.journal.error(f"{'Column':>{key_width}}: {row['column']}")
                self.journal.error(f"    {MTL_NAME:>{name_width}}: {row[MTL_NAME]}")
                self.journal.error(f"    {PIB_NAME:>{name_width}}: {row[PIB_NAME]}")

    @staticmethod
    def _display(value: Any) -> str:
        """Human readable cell value, with blanks made explicit."""
        blank_token = ""
        if value is None:
            return blank_token
        try:
            if pd.isna(value):
                return blank_token
        except (TypeError, ValueError):
            # pd.isna() is ambiguous for list-like values.
            pass
        text = str(value).strip()
        return text if text else blank_token

    def _record_name(self, row: dict[str, Any], key_columns: list[str]) -> str:
        """Readable record identifier for security-string messages."""
        if "name" in key_columns:
            return self._display(row["name"])
        return ", ".join(f"{key}={self._display(row[key])}" for key in key_columns)

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

    def _build_security_summary(
        self,
        result: SecurityComparisonResult,
        frames: _PreparedFrames,
        parse_security_strings: bool,
    ) -> SecurityComparisonSummary:
        """Translate the security phase into the values the PDF report needs."""
        return SecurityComparisonSummary(
            parsing_enabled=parse_security_strings,
            columns=list(frames.security_columns),
            records_compared=len(result.records_compared),
            failing_records=len(result.failing_records),
            strings_compared=result.strings_compared,
            mtl_pib_mismatches=result.mtl_pib_mismatches,
            matrix_failures=result.matrix_failures,
            unevaluated_strings=result.unevaluated_strings,
            samples=self._security_samples(result.results),
        )

    def _security_samples(
        self, results: list[dict[str, Any]]
    ) -> list[SecurityDifferenceRecord]:
        """One sample row per failing permission (principal)."""
        permeable = self.metadata.worksheet_has_permeable_permissions()
        settings_key = "permeable_settings" if permeable else "all_settings"
        mtl_key = "mtl_setting_effective" if permeable else "mtl_setting"
        pib_key = "pib_setting_effective" if permeable else "pib_setting"

        samples: list[SecurityDifferenceRecord] = []
        for comparison in results:
            for principal, setting in comparison.get(settings_key, {}).items():
                mtl_setting = setting[mtl_key]
                pib_setting = setting[pib_key]
                matrix_setting = setting["matrix_setting"]

                findings = []
                if mtl_setting != pib_setting:
                    findings.append("MTL/CMD and PI differ")
                if pib_setting != matrix_setting:
                    findings.append("PI does not match the matrix")
                if not findings:
                    continue

                samples.append(
                    SecurityDifferenceRecord(
                        record_name=str(comparison.get("record_name", "")),
                        column=str(comparison.get("column_name", "")),
                        principal=principal,
                        mtl_setting=mtl_setting,
                        pib_setting=pib_setting,
                        matrix_setting=matrix_setting,
                        finding="; ".join(findings),
                    )
                )
        return samples
