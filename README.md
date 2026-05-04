<p align="center">
  <img src="assets/logo.png" alt="WAVE logo" width="140" />
</p>

<h1 align="center">WAVE</h1>
<p align="center"><strong>Workbook Automation &amp; Verification Engine</strong></p>

<p align="center">
  <!-- Badges (replace ORG/REPO + workflow file names/branches as needed)
  <a href="https://github.com/M268816/wave/releases">
    <img alt="Release" src="https://img.shields.io/github/v/release/M268816/wave?sort=semver" />
  </a>
  <a href="https://github.com/M268816/wave/actions">
    <img alt="Build" src="https://img.shields.io/github/actions/workflow/status/M268816/wave/build.yml?branch=main" />
  </a>
  <a href="https://github.com/M268816/wave/issues">
    <img alt="Issues" src="https://img.shields.io/github/issues/M268816/wave" />
  </a>
  <a href="https://github.com/M268816/wave/blob/main/LICENSE">
    <img alt="License" src="https://img.shields.io/github/license/M268816/wave" />
  </a>
  <img alt="Python" src="https://img.shields.io/badge/python-3.11%2B-blue" />
</p>

---

## Overview

WAVE is a lightweight desktop application that validates and updates **MTL/CMD Excel workbooks** using **CSV inputs exported from PI Builder**.

It supports two main workflows:

- **Compare**: compare a PI Builder CSV export against the selected MTL/CMD table and report differences.
- **Append (Upsert)**: insert new records and update existing records in the selected MTL/CMD table, then output an updated workbook copy.

WAVE is intended to **increase data transfer accuracy** and **reduce validation time**.

---

## What WAVE works with

### Inputs

- **MTL/CMD workbook**: `.xlsx` / `.xlsm` containing named Excel tables
- **PI Builder export**: `.csv`

### Outputs

WAVE writes artifacts next to the executable (or project root when running from source):

- `reports/` — per-run report folders containing:
  - `*.log` run report
  - CSV snapshots/exports (examples below)
  - appended workbook copy (append workflow)
- `logs/` — general application error logs

Common per-run CSV artifacts include:

- `mtl_dataframe_before.csv` (append workflow)
- `input_dataframe.csv` (append workflow)
- `mtl_dataframe_after.csv` (append workflow)
- `rows_only_within_MTL.csv` / `rows_only_within_input.csv` (compare workflow when keys differ)
- `*_comparison.csv` (compare workflow when row contents differ)

---

## Important notes / assumptions

- **Close the MTL/CMD workbook before running WAVE.** (WAVE automates Excel via `xlwings`.)
- WAVE is tested against a specific **MTL/CMD version** defined in `assets/config.json` (see `"mtl_version"`).
- For append workflows, **do not pre-populate a `Version` column** in the input CSV; WAVE will manage this behavior during column conformance.

---

## How it works (high level)

1. Select files:
   - MTL/CMD workbook
   - PI Builder export CSV
2. Choose a target **MTL/CMD table** (worksheet/table mapping comes from `assets/config.json`)
3. Optionally enter a **Filter** string (applied to configured filter columns; some tables use key-based filtering)
4. Run:
   - **Compare** to validate
   - **Append** to upsert and generate an updated workbook copy
5. Review the generated run report and CSVs in `reports/<timestamp>_<name>/`

---

## Configuration (tables & formatting)

WAVE uses `assets/config.json` to define:

- the compatible `mtl_version`
- worksheet → `table_id` → table `type`
- whether a worksheet/table can be processed (`can_compare`)
- table formatting rules per type:
  - `index_keys` (composite keys used for uniqueness / matching)
  - filtering rules (string filtering vs key-based filtering)
  - optional object type ordering
  - sort order and direction
- dataframe formatting rules:
  - known numeric columns
  - “classic GxP” columns that can be auto-added when missing

If you add new MTL/CMD worksheets or rename tables, update `assets/config.json` accordingly.

---

## Running from source (development)

### Requirements

- Python **3.11+** (recommended)
- Microsoft Excel installed (required for `xlwings` automation)

### Setup

```bash
python -m venv .venv

# Windows:
.venv\Scripts\activate

# macOS/Linux:
source .venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Run

```bash
python -m src.main
```

> If you don't have a `requirements.txt` yet, create one (either curated or via `pip freeze > requirements.txt`)

## Building a standalone executable (Pyinstaller)

### Build tooling

```bash
python -m pip install --upgrade pip
pip install pyinstaller
```

### Build

```bash
pyinstaller wave.spec
```

Build artifacts will be under `dist/` (depending on `wave.spec`).

## Troubleshooting

### "Configuration not found. Cannot run application."

- Ensure `assets/config.json` is present and bundled for runtime.
- If running a built executable, make sure your PyInstaller spec includes `assets\`.

### Excel automation issues

- Close any open MTL/CMD workbooks.
- Confirm Excel is installed and opens normally.

### CSV encoding issues

- WAVE attempts to fallback encoding conversion of UTF-8 files and may emit a `*_fixed.csv` in the run report folder. If this automatic process fails, try to save the CSV file as a `UTF-8 encoded CSV` file via the newest version of Excel that you have available to you.

## Project Structure (suggested)

Typical Layout:

- `src/`
  - `main.py` - GUI entry point
  - `process.py` - orchestration for compare and append flows
  - `data_extraction.py` - reads MTL tables and input CSVs
  - `data_formatter.py` - normalization, conforming, sorting
  - `data_comparator.py` - comparisons and diff reporting
  - `data_appender.py` - upsert and workbook export
  - `metadata.py` - config backend, worksheet and table metadata
  - `paths.py` - runtime-safe pathing (PyInstaller + resources)
  - `reporting.py` - per run reporting and log outputs
- `assets/`
  - `logo.png`
  - `config.json`

## License

Internal use only. See [LICENSE](./LICENSE).
