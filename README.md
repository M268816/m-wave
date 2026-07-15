<p align="center">
  <img src="assets/logo.png" alt="WAVE logo" width="140" />
</p>

<h1 align="center">WAVE</h1>
<p align="center"><strong>Workbook Automation &amp; Verification Engine</strong></p>

<p align="center">
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

WAVE is a lightweight desktop application that validates and updates **Master Data Context Excel Workbooks** using **CSV inputs**.

It supports two main workflows:

- **Comparison**: compare **CSV** data against a **Master Context Excel Table** and report the differences.
- **Append (Upsert)**: insert new records and update existing records within a **Master Data Context Table**, then output an updated workbook copy.

WAVE is intended to **increase data transfer accuracy** and **reduce validation time**.

---

## What WAVE works with

### Inputs

- **MTL/CMD workbook**: `.xlsx` / `.xlsm` containing named Excel tables
- **PI Builder export**: `.csv`

_Planned_

- **MES**

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
- `comparable_rows.csv` / `non_comparable_rows.csv` (compare workflow, key-filtering step)

---

## Important notes / assumptions

- **Close any Master Data Context workbook before running WAVE.** (WAVE automates Excel via `xlwings`.)
- WAVE is tested against a specific **MTL/CMD version** defined in `assets/mtl_config.json` (see `"mtl_version"`).
- For append workflows, **do not pre-populate a `Version` column** in the input CSV; WAVE will manage this behavior during column conformance.
- **Do not change configurations or report options while a process is running.** WAVE will reject the change and restore the previous value.
- **Do not close WAVE while a process is running.** A confirmation dialog will warn you — any in-progress work will be lost.

---

## WavePacks

WavePacks are the designation given to the sub-modules that make up the GUI, logic controllers, and other processing modules for a discrete set of instructions. Each WavePack is a self-contained `WavePackFrame` subclass registered with the application at startup.

## How it works (high level, MTL-CMD example)

1. Launch WAVE — the **WavePack Launcher** is shown.
2. Select a WavePack (e.g. **MTL-CMD**). You will be locked into your WavePack for the session; restart to change.
3. Select files:
   - MTL/CMD workbook
   - PI Builder export CSV
4. Choose a target **MTL/CMD table** (worksheet/table mapping comes from `assets/mtl_config.json`)
5. Optionally enter a **Filter** string (applied to configured filter columns; some tables use key-based filtering)
6. Run:
   - **Compare** to validate a comparison between the selected files.
   - **Append** to upsert and generate an updated workbook copy.
7. Review the generated run report and CSVs in `reports/<timestamp>_<name>/`

---

## WavePack Launcher

WAVE opens with a **WavePack Launcher** screen. Each registered WavePack is listed as a button. Clicking one shows a confirmation dialog before locking you into the selection for the session.

Currently registered WavePacks:

| WavePack    | Description                                                      |
| ----------- | ---------------------------------------------------------------- |
| **MTL-CMD** | Full compare and append workflow against MTL/CMD Excel workbooks |
| **Example** | Placeholder frame for development and testing                    |

To add a new WavePack, register its `WavePackFrame` subclass in `AppWindow.init_wavepacks()` using `self.add_wavepack("Name", FrameClass)`.

---

## Configuration

WAVE uses two separate configuration files:

### MTL Configuration (`assets/mtl_config.json`)

Defines MTL/CMD-specific settings:

- The compatible `mtl_version`
- Worksheet -> `table_id` -> table `type` mappings
- Whether a worksheet/table can be processed (`can_compare`)
- Table formatting rules per type:
  - `index_keys` (composite keys used for uniqueness / matching)
  - Filtering rules (string filtering vs key-based filtering)
  - Optional object type ordering
  - Sort order and direction
- Dataframe formatting rules:
  - Known numeric columns
  - "classic GxP" columns that can be auto-added when missing

If you add new MTL/CMD worksheets or rename tables, update `assets/mtl_config.json` accordingly.

### User Preferences (`user_prefs/user_preferences.json`)

Stores user-editable settings including the active UI theme and report display options (`use_timestamps`, `use_msg_types`). On first run, WAVE bootstraps a copy from `assets/user_preferences.json` into the local `user_prefs/` folder. Subsequent runs use this copy. Changes made through the in-app **Report Options** and **Themes** menus are written back to this file automatically.

If the user preferences file becomes corrupt or is deleted, WAVE regenerates it from the bundled default.

---

## Menu Bar

| Menu               | Item                 | Description                                                                           |
| ------------------ | -------------------- | ------------------------------------------------------------------------------------- |
| **File**           | Exit                 | Close the application (prompts if a session is active)                                |
| **Report Options** | Report Timestamps    | Toggle timestamps in the process output display                                       |
| **Report Options** | Report Message Types | Toggle message-type prefixes (INFO, ERROR, etc.) in the display                       |
| **Themes**         | _(theme list)_       | Switch the UI theme at runtime; selection is persisted                                |
| **Help**           | MTL/CMD Instructions | Push bundled instructions to the output display and open reference links in a browser |
| **Help**           | About                | Display application version, copyright, and author information                        |

> Configuration changes are blocked while a process is running.

---

## Reporting

All process output is routed through the `Reporting` class (`src/app/reporting.py`). It writes to three destinations simultaneously:

1. **Process output display** — live streaming into the `ScrolledText` widget via the Tk event loop.
2. **Run log file** — a `.log` file written to `reports/<timestamp>_(<name>)/` on `save_report()`.
3. **Application error log** — a general `logs/<timestamp>_general_error.log` capturing Python-level log records.

### Output formatting helpers

| Method                        | Visual style                                           |
| ----------------------------- | ------------------------------------------------------ |
| `title(msg)`                  | Heavy box (`+=+`) -- major section start/end           |
| `subtitle(msg)`               | Light box (`+-+`) -- sub-section header                |
| `simple_title(msg)`           | Dashed inline header (`-- text --`)                    |
| `highlight_error(msg)`        | Single-line error banner (`X=== msg ===X`)             |
| `highlight_titled_error(msg)` | Boxed error with title and message (`X==+ TITLE +==X`) |
| `divider()`                   | Full-width `=` line                                    |
| `separator()`                 | Full-width `-` line                                    |
| `section()`                   | Half-width `-` line                                    |

### Modal dialogs

Popup dialogs (errors, warnings, info) raised from background threads are routed through a **modal queue** and dispatched safely on the main thread, one at a time, FIFO. This prevents overlapping dialogs and Tk thread-safety issues.

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
python main.py
```

> If you don't have a `requirements.txt` yet, create one (either curated or via `pip freeze > requirements.txt`)

## Building a standalone executable (PyInstaller)

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

### PyInstaller path resolution

WAVE uses a PyInstaller-aware path module (`src/app/paths.py`) that resolves resource and data directories correctly in both environments:

| Environment         | Resource path (assets, bundled configs) | Data path (logs, reports, user prefs) |
| ------------------- | --------------------------------------- | ------------------------------------- |
| Running from source | Project root                            | Project root                          |
| Compiled `.exe`     | `sys._MEIPASS` temp extraction folder   | Directory containing the `.exe`       |

This means logs, reports, and user preferences always appear **next to the executable**, never inside the temp extraction folder.

---

## Troubleshooting

### "Configuration not found. Cannot run application."

- Ensure `assets/mtl_config.json` is present and bundled for runtime.
- Endure the json file is properly written with no errors within json syntax.
- If running a built executable, make sure your PyInstaller spec includes `assets\`.

### Excel automation issues

- Close any open MTL/CMD workbooks.
- Confirm Excel is installed and opens normally.

### CSV encoding issues

- WAVE attempts fallback encoding conversion of non-UTF-8 files and may emit a `*_fixed.csv` in the run report folder. If this automatic process fails, try saving the CSV file as a `UTF-8 encoded CSV` file via the newest version of Excel available to you.

---

## Project Structure

```
wave/
|-- main.py                        # Entry point -- initialises logging and launches AppWindow
|-- pyproject.toml                 # Project metadata and dependency declarations
|-- requirements.txt               # Pinned runtime dependencies
|-- wave.spec                      # PyInstaller build spec
|-- assets/
|   |-- logo.png                   # Application icon
|   |-- mtl_config.json            # MTL/CMD configuration (bundled with executable)
|   |-- user_preferences.json      # Default user preferences (bundled with executable)
|   `-- instructions.txt           # Help text shown via the Help menu
|-- user_prefs/
|   `-- user_preferences.json      # User-editable preferences (auto-generated on first run)
|-- logs/
|   `-- <timestamp>_general_error.log
|-- reports/
|   `-- <timestamp>_(<filter>)/
|       |-- <filter>.log
|       `-- *.csv
`-- src/
    |-- app/                       # Application-level shared modules
    |   |-- gui.py                 # AppWindow, LauncherFrame, ExampleFrame
    |   |-- controller.py          # AppController -- reporting and config management
    |   |-- utils.py               # WavePackFrame, ProcessController, font/layout constants
    |   |-- reporting.py           # Reporting -- log/display/modal output routing
    |   `-- paths.py               # PyInstaller-aware path resolution helpers
    `-- mtl/                       # MTL-CMD WavePack modules
        |-- gui.py                 # MTLFrame -- MTL-CMD WavePack GUI
        |-- controller.py          # MTLController, MTLRequest, MTLUi, MTLProcessorType
        |-- process.py             # Process -- orchestrates compare and append workflows
        |-- extraction.py          # DataExtractor -- reads MTL named tables and input CSVs
        |-- formatter.py           # DataFormatter -- normalisation, conforming, filtering, sorting
        |-- comparator.py          # DataComparator -- shape and row-level diff reporting
        |-- appender.py            # DataAppender -- upsert logic and workbook export
        `-- metadata.py            # MtlMetadata, TableType, WORKSHEET_METADATA, TABLE_FORMATTING
```

---

## License

Internal use only. See [LICENSE](./LICENSE).

## Repositories

You can find this repo on both GitHub and Gitea. Consult the WAVE SOP for details.
