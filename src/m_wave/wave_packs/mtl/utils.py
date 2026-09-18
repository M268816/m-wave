# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH
# This tool was created with the help of AI.

# stdlib

# third party
import pandas as pd

# local core
from m_wave.core.reporting import Reporting


def report_shape_differences(
    report: Reporting, mtl_df: pd.DataFrame, input_df: pd.DataFrame
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
            report.info(f"{dimension} counts match!")
        else:
            diff = abs(mtl_dim - input_dim)
            larger, smaller = (
                ("MTL", "PI Builder") if mtl_dim > input_dim else ("PI Builder", "MTL")
            )
            report.warning(f"{larger} has {diff} more {plural} than {smaller}.")

    report.info("Tables shape comparison:")
    for key, value in comparison.items():
        report.info(f"{key:>19}:\t{value}")

    _emit(mtl_cols, input_cols, "column")
    _emit(mtl_rows, input_rows, "row")

    return (mtl_rows, input_rows, mtl_cols, input_cols)
