# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
#
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH

# stdlib

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
    Attempts to compare and report differences in supplied MTL and input data frames.
    """

    def __init__(self, report: Reporting, metadata: Metadata) -> None:
        self.report = report
        self.metadata = metadata

    def _mask_matching_cells(
        self,
        diffs: pd.DataFrame,
        key_columns: list[str],
        df1_name: str = "MTL",
        df2_name: str = "Input",
    ) -> pd.DataFrame:
        """
        Blank out value pairs that actually match, so each row shows only
        the columns that genuinely differ. Rows left with no differences
        at all are dropped.
        """
        out = diffs.copy()
        suffix_1, suffix_2 = f"_{df1_name}", f"_{df2_name}"

        bases = [
            col[: -len(suffix_1)]
            for col in out.columns
            if col.endswith(suffix_1)
            and f"{col[: -len(suffix_1)]}{suffix_2}" in out.columns
        ]

        any_diff = pd.Series(False, index=out.index)

        for base in bases:
            left, right = f"{base}{suffix_1}", f"{base}{suffix_2}"
            a, b = out[left], out[right]

            both_null = a.isna() & b.isna()
            equal = (a == b) | both_null

            out.loc[equal, [left, right]] = pd.NA
            any_diff |= ~equal

            # Drop the pair entirely if nothing differs anywhere
            if not any_diff.any() and not (~equal).any():
                out = out.drop(columns=[left, right])

        return out.loc[any_diff].copy()

    def compare(
        self, mtl_dataframe: pd.DataFrame, input_dataframe: pd.DataFrame, sort_fn=None
    ) -> bool:
        """
        Uses datacompy instead of my hand rolled mess.
        """

        self.report.info("Obtaining the table index keys from metadata...")

        key_columns = self.metadata.get_table_index_keys()

        if mtl_dataframe.empty:
            self.report.error(
                "There was a problem returning the MTL data. Empty table detected. "
                + "Stopping the process."
            )
            return False
        if input_dataframe.empty:
            self.report.error(
                "There was a problem returning the PI Builder data. "
                + "Empty table detected. Stopping the process."
            )
            return False

        report_shape_differences(self.report, mtl_dataframe, input_dataframe)

        self.report.info("Comparing...")
        lc_key_columns: list = [column.lower() for column in key_columns]

        # Exclude Manual Verificaiton Columns like datasecurity and ptsecurity
        # Make these a configuration later instead of hard coded.
        excluded_cols = ["datasecurity", "ptsecurity"]
        manual_cols = [c.lower() for c in excluded_cols]
        excluded = [
            c for c in manual_cols if c in excluded_cols or c in input_dataframe.columns
        ]

        if excluded:
            self.report.warning(
                "The following columns are EXCLUDED from this comparison."
            )
            for col in excluded:
                self.report.warning(f"\t{col}")
            self.report.warning(
                "These columns require a manual check by the reviewr by design.\n "
                + "they are reconfigured for the master tag list and differences\n"
                + "here are expected, and not defects or artifacts."
            )

        comparison = datacompy.PandasCompare(
            mtl_dataframe.drop(columns=excluded, errors="ignore"),
            input_dataframe.drop(columns=excluded, errors="ignore"),
            join_columns=lc_key_columns,
            df1_name="MTL",
            df2_name="Input",
        )

        self.report.info(
            "Any non matching records are now being recorded. "
            + "Any records within these files could not be compared, "
            + "and manual fixes will be needed."
        )
        comparison.df1_unq_rows.to_csv(
            self.report.report_folder / "mtl_non_matching_records.csv", index=False
        )
        comparison.df2_unq_rows.to_csv(
            self.report.report_folder / "input_non_matching_records.csv", index=False
        )

        self.report.info(
            "Matching records that were compared are now being recorded. "
            + "Any records within this file was successfuly compared, "
            + "but may contain errors."
        )
        diffs = comparison.all_mismatch(ignore_matching_cols=True)
        diffs = self._mask_matching_cells(diffs, lc_key_columns)

        diffs.to_csv(
            self.report.report_folder
            / f"{self.report.cleaned_name}_final_comparison.csv",
            index=False,
        )

        matching_comparison = comparison.matches()

        if not matching_comparison:
            self.report.info("Differences found.")
            self.report.info("Reporting the differences below:")

            filtered_diff = diffs.drop(columns=lc_key_columns, errors="ignore")
            all_null_rows = filtered_diff.isna().all(axis=1)
            significant_diffs = diffs.loc[~all_null_rows]

            for index, record in significant_diffs.iterrows():
                self.report.error_divider()
                self.report.error(f"Record: {index}")

                first_column = lc_key_columns[0]
                self.report.error(
                    f"  {first_column.capitalize()}: {record[first_column]}"
                )

                max_text_len = max(len(column) for column in lc_key_columns)
                for column in lc_key_columns[1:]:
                    self.report.error(
                        f"    {column.capitalize():>{max_text_len}}: {record[column]}"
                    )

                # Find only the columns that actually differ by
                # scanning for _MTL / _Input pairs
                for col in significant_diffs.columns:
                    if not col.endswith("_MTL"):
                        continue
                    base = col[: -len("_MTL")]
                    # strip the suffix to get the base col name
                    if base.lower() in manual_cols:
                        continue

                    mtl_val = record[f"{base}_MTL"]
                    inp_val = record[f"{base}_Input"]

                    is_nan = pd.isna(mtl_val) and pd.isna(inp_val)
                    if is_nan:  # type: ignore
                        continue

                    if mtl_val != inp_val:  # only report actual differences
                        self.report.error_section()
                        self.report.error(f"  Column: {base}")
                        self.report.error("     Diffs:")
                        self.report.error("         MTL:")
                        self.report.error(f"            {mtl_val:>13}")
                        self.report.error("       Input:")
                        self.report.error(f"            {inp_val:>13}")
        else:
            self.report.subtitle(" 🎉 COMPARISON IS SOUND 🎉 ")
            self.report.info(" 🎉 COMPARISON IS SOUND 🎉 ", popup=True)
            self.report.simple_title("Check that all comparison files are blank.")
            self.report.info("Blank files are a good thing here!")

        self.report.save_report()
        return matching_comparison
