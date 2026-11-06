# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH
# This tool was created with the help of AI.

# stdlib
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path

# third party
import pandas as pd
import ttkbootstrap as tkb
from ttkbootstrap import ScrolledText

from m_wave.core.reporting.reporter import Reporter

# local core


@dataclass
class MTLUiPayload:
    """
    Data class that captures the extension's UI for manipulation during processing.
    """

    progress_bar: tkb.Progressbar
    process_button: tkb.Button
    opt_process: tkb.StringVar
    text_box: ScrolledText
    mtl_version: tkb.StringVar
    mtl_path: tkb.StringVar
    pib_path: tkb.StringVar


class MTLEnvironmentTypes(str, Enum):
    """
    Enum for the MTL process type selection.
    Processes should determine if they should exclude special keys when comparing
    like or differing environments. Like environments should check keys like
    security strings for differences, differing environments will always have artifacts
    with these types of keys and should be updated manually by the user.
    """

    NONE = "none"
    SAME = "same"
    DIFF = "different"


class MTLProcessorType(str, Enum):
    """
    Enum for the MTL process type selection.
    """

    NONE = "none"
    COMPARE = "compare"
    APPEND = "append"
    DOWNLOAD = "download"


@dataclass(frozen=True)
class MTLProcessorRequest:
    """
    Data class that captures a user request for the MTL process.
    """

    process_type: MTLProcessorType
    user: str
    start_datetime: datetime
    env_types: MTLEnvironmentTypes
    filter: str
    mtl_table_name: str
    mtl_file_path: Path
    pib_file_path: Path

    @property
    def report_name(self) -> str | None:
        return self.filter or None


def report_shape_differences(
    report: Reporter, mtl_df: pd.DataFrame, input_df: pd.DataFrame
) -> tuple:
    """
    Reports the dimensions of the input data frames and returns that info in a tuple by:
    (mtl_rows, input_rows, mtl_cols, input_cols)
    """
    mtl_rows = mtl_df.shape[0]
    mtl_cols = mtl_df.shape[1]

    input_rows = input_df.shape[0]
    input_cols = input_df.shape[1]

    comparison = {
        "shapes_equal": mtl_df.shape == input_df.shape,
        "mtl_rows": mtl_rows,
        "mtl_cols": mtl_cols,
        "input_rows": input_rows,
        "input_cols": input_cols,
        "row_difference": abs(mtl_rows - input_rows),
        "column_difference": abs(mtl_cols - input_cols),
    }

    def _emit(mtl_dim, input_dim, dimension):
        plural = f"{dimension}s"
        if mtl_dim == input_dim:
            report.journal.info(f"{dimension} counts match!")
        else:
            diff = abs(mtl_dim - input_dim)
            larger, smaller = (
                ("MTL", "PI Builder") if mtl_dim > input_dim else ("PI Builder", "MTL")
            )
            report.journal.warning(f"{larger} has {diff} more {plural} than {smaller}.")

    report.journal.info("Tables shape comparison:")
    for key, value in comparison.items():
        report.journal.info(f"{key:>19}:\t{value}")

    _emit(mtl_cols, input_cols, "column")
    _emit(mtl_rows, input_rows, "row")

    return (mtl_rows, input_rows, mtl_cols, input_cols)
