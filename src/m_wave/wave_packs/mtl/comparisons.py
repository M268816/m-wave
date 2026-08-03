# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
#
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH

# stdlib

# third party
import pandas as pd
import datacompy

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

    def compare(
        self, mtl_dataframe: pd.DataFrame, input_dataframe: pd.DataFrame, sort_fn=None
    ) -> bool:
        """
        Uses datacompy instead of my hand rolled mess.
        """

        self.report.info("Obtaining the table index keys from metadata...")

        key_ring = self.metadata.get_table_index_keys()

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
        join_keys = [key.lower() for key in key_ring]
        comparison = datacompy.PandasCompare(
            mtl_dataframe,
            input_dataframe,
            join_columns=join_keys,
            df1_name="MTL",
            df2_name="Input",
        )

        self.report.info("Saving unique records to a csv file.")
        comparison.df1_unq_rows.to_csv(
            self.report.report_folder / "mtl_non_matching_records.csv", index=False
        )
        comparison.df2_unq_rows.to_csv(
            self.report.report_folder / "input_non_matching_records.csv", index=False
        )

        self.report.info("Saving all comparable records to a csv file.")
        diffs = comparison.all_mismatch(ignore_matching_cols=True)
        diffs.to_csv(
            self.report.report_folder
            / f"{self.report.cleaned_name}_matching_record_comparison.csv",
            index=False,
        )

        matched = comparison.matches()

        if not matched:
            self.report.info("Differences found.")
            self.report.info("Reporting the differences below:")
            for _, s in diffs.iterrows():
                # Build the record identifier from the index keys
                key_info = ", ".join(
                    f"{k.capitalize()}: {s[k]}" for k in join_keys if k in s.index
                )
                self.report.error_divider()
                self.report.error(f"Record: [{key_info}]")
                self.report.error_divider()

                # Find only the columns that actually differ by
                # scanning for _MTL / _Input pairs
                for col in diffs.columns:
                    if not col.endswith("_MTL"):
                        continue
                    base = col[
                        : -len("_MTL")
                    ]  # strip the suffix to get the base col name
                    mtl_val = s[f"{base}_MTL"]
                    inp_val = s[f"{base}_Input"]

                    is_nan = pd.isna(mtl_val) and pd.isna(inp_val)
                    if is_nan:  # type: ignore
                        continue

                    if mtl_val != inp_val:  # only report actual differences
                        self.report.error(f"  Column : {base}")
                        self.report.error_section()
                        self.report.error(f"       MTL : {mtl_val}")
                        self.report.error(f"     Input : {inp_val}")
                        self.report.error_separator()

        self.report.save_report()
        return matched
