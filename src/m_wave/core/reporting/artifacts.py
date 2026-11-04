# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH
# This tool was created with the help of AI.

"""
Artifacts: the comparison files a technical reviewer can open and check.

    artifacts.copy_in(file_1, "before_file_1.xlsx", "File 1 as received")
    artifacts.save_csv("after_file_1.csv", formatted_df, "File 1 after formatting")
    artifacts.save_csv("missing_in_file_2.csv", missing_rows, "In File 1, not in File 2",
                       headers=["Key", "Value"])
    artifacts.save_csv("comparison.csv", comparison_df, "Row-by-row comparison")

    # For files you write yourself (openpyxl, matplotlib, ...):
    path = artifacts.path_for("comparison.xlsx", "Comparison workbook")
    workbook.save(path)

Files are saved in the run folder:
    reports/(<timestamp>)_<name>/artifacts/

Every saved file is written to the Journal with its description, and the
Reporter lists them all again at the end of the journal.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from m_wave.core.reporting.journal import Journal


# stdlib
import csv
import shutil
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# local
from m_wave.core.reporting.debug_log import DebugLog


@dataclass
class Artifact:
    """One saved file."""

    path: Path
    description: str

    @property
    def name(self) -> str:
        return self.path.name


class Artifacts:
    """
    Saves comparison files into the current run's artifacts folder.

    The Reporter calls ``start`` when a run starts and ``finish`` when it ends.
    Your processor only uses the save methods.
    """

    def __init__(self, journal: Journal) -> None:
        self.journal = journal
        self.folder: Path | None = None
        self.saved: list[Artifact] = []
        self._debug = DebugLog()

    # -------------------------------------------------------------------------
    # Run start / finish (used by the Reporter)
    # -------------------------------------------------------------------------
    def start(self, folder: Path) -> None:
        self.folder = folder
        self.saved = []

    def finish(self) -> None:
        self.folder = None

    # -------------------------------------------------------------------------
    # Saving
    # -------------------------------------------------------------------------
    def path_for(self, filename: str, description: str) -> Path:
        """
        Get a path in the artifacts folder for a file you will write yourself.
        The file is listed in the journal straight away.
        """
        path = self._folder() / filename
        self._remember(path, description)
        return path

    def save_csv(
        self,
        filename: str,
        data: Any,
        description: str,
        headers: Sequence[str] | None = None,
    ) -> Path:
        """
        Save a table as CSV.

        data: a pandas DataFrame, or a list of rows (each row a list/tuple).
              For a list of rows, pass ``headers`` to add a header row.
        """
        path = self._folder() / filename

        if hasattr(data, "to_csv"):  # pandas DataFrame
            data.to_csv(path, index=False, encoding="utf-8-sig")
            row_count = len(data)
        else:
            rows = list(data)
            # utf-8-sig lets Excel open the file with the right characters.
            with open(path, "w", newline="", encoding="utf-8-sig") as file:
                writer = csv.writer(file)
                if headers:
                    writer.writerow(headers)
                writer.writerows(rows)
            row_count = len(rows)

        self._remember(path, f"{description} ({row_count:,} rows)")
        return path

    def save_text(self, filename: str, text: str, description: str) -> Path:
        """Save plain text, for example a list of sheet names or a config dump."""
        path = self._folder() / filename
        path.write_text(text, encoding="utf-8")
        self._remember(path, description)
        return path

    def save_lines(self, filename: str, lines: Iterable[str], description: str) -> Path:
        """Save one item per line, for example a list of missing keys."""
        return self.save_text(filename, "\n".join(lines) + "\n", description)

    def copy_in(self, source: Path, filename: str, description: str) -> Path:
        """
        Copy a file into the artifacts folder unchanged. Use this for the
        "before" snapshot of an input file.
        """
        path = self._folder() / filename
        shutil.copy2(source, path)
        self._remember(path, description)
        return path

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------
    def _folder(self) -> Path:
        if self.folder is None:
            raise RuntimeError(
                "No run has started. Call reporter.start_run() before saving artifacts."
            )
        self.folder.mkdir(parents=True, exist_ok=True)
        return self.folder

    def _remember(self, path: Path, description: str) -> None:
        self.saved.append(Artifact(path, description))
        self.journal.info(f"Saved artifact: {path.name} - {description}")
        self._debug.debug("Artifact path: %s", path)
