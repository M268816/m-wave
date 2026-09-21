# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH
# This tool was created with the help of AI.

# stdlib
from typing import Any

# third party
import datacompy
import pandas as pd

# local core
from m_wave.core.reporting import Reporting

# local wave pack
from m_wave.wave_packs.mtl.metadata import Metadata
from m_wave.wave_packs.mtl.utils import report_shape_differences


class Comparisons:
    """
    Compares a Master Tag List (MTL) table against a PI Builder input table.

    datacompy owns the comparison. This class only decides what to exclude,
    and how to render what datacompy found. A blank on one side and a value
    on the other is a difference and is always reported.
    """

    def __init__(self, report: Reporting, metadata: Metadata) -> None:
        self.report = report
        self.metadata = metadata
        self.manual_review_columns = self.metadata.dataframe_formatting[
            "manual_review_columns"
        ]

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
        input_dataframe: pd.DataFrame,
        sort_fn=None,
    ) -> bool:
        """
        Compare the MTL against the PI Builder input. Returns datacompy's
        verdict: True only when every record matched on every compared column.
        """
        df1_name, df2_name = "MTL", "Input"

        self.report.info("Obtaining the table index keys from metadata...")
        key_columns = [c.lower() for c in self.metadata.get_table_index_keys()]

        if mtl_dataframe.empty:
            self.report.error(
                "There was a problem returning the MTL data. Empty table detected. "
                "Stopping the process."
            )
            return False
        if input_dataframe.empty:
            self.report.error(
                "There was a problem returning the PI Builder data. "
                "Empty table detected. Stopping the process."
            )
            return False

        report_shape_differences(self.report, mtl_dataframe, input_dataframe)
        self.report.info("Comparing...")

        # Lowercase up front so exclusions and key names line up with the
        # names datacompy uses internally.
        mtl = mtl_dataframe.rename(columns=str.lower)
        inp = input_dataframe.rename(columns=str.lower)

        excluded = sorted(
            {c for c in mtl.columns if c in self.manual_review_columns}
            | {c for c in inp.columns if c in self.manual_review_columns}
        )

        if excluded:
            self.report.warning(
                "The following columns are EXCLUDED from this comparison."
            )
            for column in excluded:
                self.report.warning(f"\t- {column}")
            self.report.warning(
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
            self.report.error(
                "Cannot compare. These index key columns are missing from one or "
                f"both tables: {', '.join(missing)}"
            )
            self.report.save_report()
            return False

        comparison = datacompy.PandasCompare(
            mtl,
            inp,
            join_columns=key_columns,
            df1_name=df1_name,
            df2_name=df2_name,
        )

        # unmatched records
        self.report.simple_title("Any non matching records are now being recorded.")
        self.report.info(
            "Any records within these files could not be compared, "
            "and manual fixes will be needed."
        )
        comparison.df1_unq_rows.to_csv(
            self.report.report_folder / "mtl_non_matching_records.csv", index=False
        )
        comparison.df2_unq_rows.to_csv(
            self.report.report_folder / "input_non_matching_records.csv", index=False
        )
        if not comparison.df1_unq_rows.empty:
            self.report.error(
                f"{len(comparison.df1_unq_rows)} record(s) exist only in the "
                f"{df1_name}. See mtl_non_matching_records.csv."
            )
        if not comparison.df2_unq_rows.empty:
            self.report.error(
                f"{len(comparison.df2_unq_rows)} record(s) exist only in the "
                f"{df2_name}. See input_non_matching_records.csv."
            )

        # differing cells
        self.report.simple_title(
            "Matching records that were compared are now being recorded."
        )
        self.report.info(
            "Any records within this file were successfully compared, but may "
            "contain errors."
        )

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
            self.report.error(
                "Could not locate any <column>_match / value pairs on "
                f"intersect_rows using suffixes {suffix_1!r} and {suffix_2!r}. "
                f"Columns present: {list(intersect.columns)}"
            )
            self.report.save_report()
            return False

        long_rows: list[dict[str, Any]] = []
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

        long_form = pd.DataFrame(
            long_rows, columns=[*key_columns, "column", df1_name, df2_name]
        )

        base = self.report.report_folder / self.report.cleaned_name
        long_form.to_csv(f"{base}_differences_by_cell.csv", index=False)
        comparison.all_mismatch(ignore_matching_cols=True).to_csv(
            f"{base}_final_comparison.csv", index=False
        )

        matches = comparison.matches()

        if not long_form.empty:
            self.report.info(
                f"{len(long_form)} differing cell(s). Reporting the differences below:"
            )
            key_width = max(len(k) for k in key_columns)
            name_width = max(len(df1_name), len(df2_name))

            for number, (keys, group) in enumerate(
                long_form.groupby(key_columns, dropna=False, sort=False), start=1
            ):
                keys = keys if isinstance(keys, tuple) else (keys,)
                self.report.error_divider()
                self.report.error(f"Record {number}:")
                for key, value in zip(key_columns, keys):
                    self.report.error(f"  {key:>{key_width}}: {self._display(value)}")

                for _, row in group.iterrows():
                    self.report.error_section()
                    self.report.error(f"  Column: {row['column']}")
                    self.report.error("     Diffs:")
                    self.report.error(f"    {df1_name:>{name_width}}: {row[df1_name]}")
                    self.report.error(f"    {df2_name:>{name_width}}: {row[df2_name]}")

            self.report.error_divider()
            self.report.error("Differences by column:")
            counts = long_form["column"].value_counts()
            width = max(len(str(c)) for c in counts.index)
            for column, count in counts.items():
                self.report.error(f"  {column!s:>{width}}: {count}")

        elif not matches:
            self.report.info(
                "Every compared cell matched, but datacompy still reports a "
                "mismatch. Unmatched records or column set differences remain. "
                "Full datacompy report:"
            )
            for line in comparison.report().splitlines():
                self.report.error(line)

        else:
            self.report.simple_title(" 🎉 COMPARISON IS SOUND 🎉 ")
            self.report.info(
                " 🎉 COMPARISON IS SOUND 🎉 ", popup=True, log=False, report=False
            )
            self.report.simple_title("Check that all comparison files are blank.")
            self.report.info("Blank files are a good thing here!")

        self.report.save_report()
        return matches
