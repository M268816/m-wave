# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
#
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH

# stdlib
from datetime import datetime

# third party
from pathlib import Path
import pandas as pd

# local
from src.app.reporting import Reporting
from src.app.utils import DATETIME_FORMAT_MERCK, USER


class Process:

    def __init__(self, report: Reporting, csv_path_1: Path, csv_path_2: Path) -> None:
        self.report = report
        self.csv_path_1 = csv_path_1
        self.csv_path_2 = csv_path_2

    def extract_csv(self, csv_input: Path) -> pd.DataFrame:
        return pd.read_csv(csv_input)

    def save_df_as_csv(self, df: pd.DataFrame, output_filename: str) -> None:
        output = self.report.report_folder / (output_filename + ".csv")
        df.to_csv(output, index=False)

    def sort(self, df: pd.DataFrame) -> pd.DataFrame:
        df_sorted = df.sort_values(by="Tag Name")
        df_sorted = df_sorted.reset_index(drop=True)
        return df_sorted

    def compare(self, df_1: pd.DataFrame, df_2: pd.DataFrame) -> bool:
        self.validate_key(df_1, "Tag Name", "input_1")
        self.validate_key(df_2, "Tag Name", "input_2")

        df_1_keyed = df_1.set_index("Tag Name")
        df_2_keyed = df_2.set_index("Tag Name")

        tags_only_in_df_1 = df_1_keyed.index.difference(df_2_keyed.index)
        tags_only_in_df_2 = df_2_keyed.index.difference(df_1_keyed.index)

        common = df_1_keyed.index.intersection(df_2_keyed.index)
        df_common_1 = df_1_keyed.loc[common].sort_index()
        df_common_2 = df_2_keyed.loc[common].sort_index()

        df_c = df_common_1.compare(df_common_2, result_names=("CSV_1", "CSV_2"))

        is_sound = df_c.empty and tags_only_in_df_1.empty and tags_only_in_df_2.empty

        if not is_sound:
            if not df_c.empty:
                self.save_df_as_csv(df_c.reset_index(), "mismatches")
            if not tags_only_in_df_1.empty:
                self.save_df_as_csv(
                    df_1_keyed.loc[tags_only_in_df_1].reset_index(),
                    "tags_only_in_input_1",
                )
            if not tags_only_in_df_2.empty:
                self.save_df_as_csv(
                    df_2_keyed.loc[tags_only_in_df_2].reset_index(),
                    "tags_only_in_input_2",
                )

        return is_sound

    def validate_key(self, df: pd.DataFrame, key: str, label: str) -> None:
        if key not in df.columns:
            raise ValueError(f"{label} is missing required column '{key}'")

        missing_keys = df[df[key].isna()]

        if not missing_keys.empty:
            self.save_df_as_csv(
                missing_keys,  # type: ignore
                f"missing_{self.filesafe_str(key)}_{self.filesafe_str(label)}",
            )
            raise ValueError(f"{label} contains blank values in '{key}'")

        duplicates = df[df[key].duplicated(keep=False)]

        if not duplicates.empty:
            self.save_df_as_csv(
                duplicates.sort_values(by=key),  # type: ignore
                f"duplicate_{self.filesafe_str(key)}_{self.filesafe_str(label)}",
            )
            raise ValueError(f"{label} contains duplicate values in '{key}'")

    def filesafe_str(self, text: str) -> str:
        return text.replace(" ", "_").lower()

    def run(self) -> None:
        self.report.title("Kepware CSV Export Comparison")
        merck_time = datetime.now().strftime(DATETIME_FORMAT_MERCK)
        self.report.subtitle(f"Started by: {USER} on {merck_time}")

        self.report.simple_title("Extraction Phase")

        self.report.info("Extracting CSV 1 into a DataFrame.")
        df_1 = self.extract_csv(self.csv_path_1)
        self.report.info("Completed.")

        self.report.info("Extracting CSV 2 into a DataFrame.")
        df_2 = self.extract_csv(self.csv_path_2)
        self.report.info("Completed.")

        self.report.simple_title("Sorting Phase")

        self.report.info("Sorting DataFrame 1 by 'Tag Name' column.")
        df_1 = self.sort(df_1)
        self.report.info("Completed.")

        self.report.info("Sorting DataFrame 2 by 'Tag Name' column.")
        df_2 = self.sort(df_2)
        self.report.info("Completed.")

        self.report.simple_title("Comparison Phase")

        self.report.info("Comparing DataFrames...")
        comparison_is_sound = self.compare(df_1, df_2)
        self.report.info("Completed.")

        self.report.simple_title("Reporting Phase")

        self.save_df_as_csv(df_1, "input_1_sorted")
        self.save_df_as_csv(df_2, "input_2_sorted")

        if comparison_is_sound:
            self.report.info("Comparison is sound, log and files ready for review.")
        else:
            self.report.info("Comparison failed, log and files ready for review.")
            self.report.info(
                "Erroneous data can be found in the 'mismatches.csv' file."
            )

        self.report.save_report()
