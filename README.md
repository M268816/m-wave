<p align="center">
  <img src="src/m_wave/assets/images/logo.png" alt="M-WAVE logo" width="140" />
</p>

<h1 align="center">M-WAVE</h1>
<p align="center"><strong>Workbook Automation &amp; Verification Engine</strong></p>

<p align="center">
  <img alt="Version" src="https://img.shields.io/badge/version-1.0.1-green" />
  <img alt="Python" src="https://img.shields.io/badge/python-3.11%2B-blue" />
  <img alt="Platform" src="https://img.shields.io/badge/platform-Windows-lightgrey" />
  <a href="https://gitlab-ce.merckgroup.com/jaffreydatasystems/m-wave/-/issues">
    <img alt="Issues" src="https://img.shields.io/badge/issues-GitLab-orange" />
  </a>
</p>

---

## Overview

M-WAVE is a lightweight desktop application that validates and updates **Master Data Context Excel Workbooks** using **CSV inputs**.

It supports two main workflows:

- **Compare** — compare CSV data against a Master Context Excel Table and report the differences.
- **Append (Upsert)** — insert new records and update existing records within a Master Data Context Table, then output an updated workbook copy.

M-WAVE is intended to **increase data transfer accuracy** and **reduce validation time**.

---

## What M-WAVE Works With

### Inputs

- **MTL/CMD workbook** — `.xlsx` / `.xlsm` containing named Excel tables
- **PI Builder export** — `.csv`

### Outputs

M-WAVE creates and writes to files and folders next to the executable (or project root when running from source):

- `generated/reports/`
  - per-run report folders named `TIMESTAMP_(table_filter_processtype)/` containing:
    - a run report log.
    - formatting before and after snapshots of the input data
    - wide table, and single one for one table comparison data
    - (for appending) a copy of the MTL with updated and appended data.
- `generated/mtl/` - user facing table configurations for the MTL process.
- `generated/logs/` - general application error logs
- `user_prefs/` - session persistant user preferences

Common per-run CSV artifacts:

| Workflow  | File                                                                        |
| --------- | --------------------------------------------------------------------------- |
| Append    | `mtl_dataframe_before.csv`, `input_dataframe.csv`, `mtl_dataframe_after.csv` |
| Compare   | `rows_only_within_MTL.csv`, `rows_only_within_input.csv`, `*_comparison.csv`, `comparable_rows.csv`, `non_comparable_rows.csv` |

---

## Important Notes / Assumptions

- **Close any MTL/CMD workbook before running M-WAVE.** M-WAVE automates Excel via `xlwings`.
- For append workflows, **do not pre-populate a `Version` column** in the input CSV — M-WAVE manages this during column conformance.
- **Do not change configurations or report options while a process is running.** M-WAVE will reject the change and restore the previous value.
- **Do not close M-WAVE while a process is running.** A confirmation dialog will warn you - any in-progress work will be lost.

---

## WavePacks

WavePacks are the modular units that make up M-WAVE. Each WavePack is a self-contained `WavePackFrame` subclass that bundles its own GUI (`gui.py`), controller (`controller.py`), and processing logic. WavePacks are registered with the application at startup in `App.init_wavepacks()`.

Currently registered WavePacks:

| WavePack                      | Description                                                      |
| ----------------------------- | ---------------------------------------------------------------- |
| **Master Tag List Processor** | Full compare and append workflow against MTL/CMD Excel workbooks |
| **Example Package**           | Placeholder frame for development and testing                    |

To add a new WavePack, register its `WavePackFrame` subclass in `App.init_wavepacks()` inside `src/m_wave/core/gui.py`:

```python
self.add_wavepack("My WavePack Name", MyWavePackFrame, "Short description.")
```

The only official validated WavePack is for the **Master Tag List Processor**. Using other custom built WavePacks, or building your own and bundling them in your own version of the M-WAVE must not be used in official validation protocols. Any attempts to use unofficial WavePacks may lead to lost work or unwanted deviations and R.O.Es.

---

## How It Works (MTL Example)

1. Launch the M-WAVE executable - the **WavePack Launcher** is shown.
2. Select a WavePack (e.g. **Master Tag List Processor**). You are locked into your WavePack for the session; and must restart to change.
3. Select files:
   - MTL/CMD workbook (`.xlsx` / `.xlsm`) - or use **Import** to download the latest MTL from the web
   - PI Builder export (`.csv`)
4. Choose a target **MTL/CMD table** from the dropdown (mappings come from `mtl_config.json`)
5. Optionally enter a **Filter** string (applied to configured filter columns; some tables use key-based filtering)
6. Select a process type:
   - **Compare** - validate differences between selected files
   - **Append** - upsert and generate an updated workbook copy
7. Review the generated run report and CSVs in:
   ```
   generated/reports/TIMESTAMP_(table_filter_processtype)/
   ```

---

## Menu Bar

| Menu               | Item                    | Description                                                                             |
| ------------------ | ----------------------- | --------------------------------------------------------------------------------------- |
| **File**           | Exit                    | Close the application (prompts confirmation if a session is active)                     |
| **Report Options** | Report Timestamps       | Toggle timestamps in the process output display                                         |
| **Report Options** | Report Message Types    | Toggle message-type prefixes (INFO, ERROR, etc.) in the display                         |
| **Themes**         | _(theme list)_          | Switch the UI theme at runtime; selection is persisted to `user_preferences.json`       |
| **Help**           | MTL/CMD Instructions    | Push bundled instructions to the output display and open reference links in a browser   |
| **Help**           | About                   | Display application version, copyright, and author information                          |

> Configuration changes are blocked while a process is running.

---

## Configuration

### MTL Configuration (`src/m_wave/assets/configurations/mtl_config.json`)

Defines MTL/CMD-specific settings:

- Compatible `mtl_version`
- Worksheet → `table_id` → table `type` mappings
- Whether a table supports compare/append (`can_compare`)
- Per-table formatting rules:
  - `index_keys` — composite keys used for uniqueness / row matching
  - Filtering rules (string filtering vs key-based filtering)
  - Optional object-type ordering
  - Sort order and direction
- Dataframe formatting rules:
  - Known numeric columns
  - "Classic GxP" columns that can be auto-added when missing

If you add new MTL/CMD worksheets or rename tables, update this file accordingly.

### User Preferences (`user_prefs/user_preferences.json`)

Stores user-editable settings including the active UI theme and report display options (`use_timestamps`, `use_msg_types`). On first run, M-WAVE bootstraps a copy from the bundled default at `src/m_wave/assets/configurations/user_preferences.json`. Changes made via the **Report Options** and **Themes** menus are written back automatically.

If this file becomes corrupt or is deleted, M-WAVE regenerates it from the bundled default.

---

## Reporting

All process output is routed through the `Reporting` class (`src/m_wave/core/reporting.py`). It writes to three destinations simultaneously:

1. **Process output display** — live streaming into the `ScrolledText` widget via the Tk event loop.
2. **Run log file** — a `.log` file written to `generated/reports/TIMESTAMP_(name)/` on `save_report()`.
3. **Application error log** — a general `generated/logs/TIMESTAMP_general_error.log` capturing Python-level log records.

### Output Formatting Helpers

| Method                        | Visual style                                             |
| ----------------------------- | -------------------------------------------------------- |
| `title(msg)`                  | Heavy box (`+=+`) — major section start/end              |
| `subtitle(msg)`               | Light box (`+-+`) — sub-section header                   |
| `simple_title(msg)`           | Dashed inline header (`-- text --`)                      |
| `highlight_error(msg)`        | Single-line error banner (`X=== msg ===X`)               |
| `highlight_titled_error(msg)` | Boxed error with title and message (`X==+ TITLE +==X`)   |
| `divider()`                   | Full-width `=` line                                      |
| `separator()`                 | Full-width `-` line                                      |
| `section()`                   | Half-width `-` line                                      |

### Modal Dialogs

Popup dialogs raised from background threads are routed through a **modal queue** and dispatched safely on the main thread, one at a time, FIFO. This prevents overlapping dialogs and Tk thread-safety issues.

---

## Running from Source (Development)

### Requirements

- [`uv`](https://docs.astral.sh/uv/) — fast Python package/venv manager. Install via `scoop install uv`, `winget install astral-sh.uv`, or see the [uv install docs](https://docs.astral.sh/uv/getting-started/installation/).
- Python **3.11+** — `uv` can locate an existing 3.11 install or download and manage its own automatically, so no manual system-wide Python install is strictly required.
- Microsoft Excel installed (required for `xlwings` automation)
- Windows

> **Multiple Python installs on one machine?** (e.g. one via the official Windows installer, another via Scoop or another manager) Don't rely on whichever `python` happens to resolve first on `PATH` — that ordering can change between sessions and silently produce a `.venv` built against the wrong interpreter. Every command below pins the interpreter explicitly (`uv venv --python 3.11` and `--python .venv\Scripts\python.exe`), so the result is the same no matter what else is installed or how `PATH` is ordered.

### Quick Start

Use the included `setup.bat` to create the virtual environment and install dependencies, then `run.bat` to launch:

```bat
setup.bat
run.bat
```

`setup.bat` uses `uv` to:

1. Create `.venv` pinned to Python 3.11 — `uv venv --python 3.11 .venv` — regardless of what plain `python` resolves to on `PATH`.
2. Install everything in `requirements.txt` into that venv.
3. Install the `m_wave` package itself in editable mode (`-e .`).

### Manual Setup

```bat
uv venv --python 3.11 .venv
uv pip install -r requirements.txt --python .venv\Scripts\python.exe
uv pip install -e . --python .venv\Scripts\python.exe
```

Or, with the venv activated, drop the `--python` flag:

```bat
.venv\Scripts\activate
uv pip install -r requirements.txt
uv pip install -e .
```

> **Note on `requirements.txt`:** `gitleaks` (the secret scanner) is intentionally **not** listed there — it's a standalone Go binary, not a Python package, so pip/uv cannot install it that way. Install it separately, e.g. `scoop install gitleaks`.

### Run

```bat
python -m m_wave
```

or, after `pip install -e .`:

```bat
m-wave
```

---

## Building a Standalone Executable (PyInstaller)

```bat
.venv\Scripts\activate
uv pip install pyinstaller
pyinstaller wave.spec
```

Build artifacts will be placed under `dist/`.

### PyInstaller Path Resolution

M-WAVE uses a PyInstaller-aware path module (`src/m_wave/core/paths.py`) that resolves resource and data directories correctly in both environments:

| Environment         | Resource path (assets, bundled configs)  | Data path (logs, reports, user prefs)   |
| ------------------- | ---------------------------------------- | --------------------------------------- |
| Running from source | `src/m_wave/` (package root)             | `m-wave/generated/` (project root)      |
| Compiled `.exe`     | `sys._MEIPASS` temp extraction folder    | Directory containing the `.exe`         |

Logs, reports, and user preferences always appear **next to the executable**, never inside the temp extraction folder.

---

## Troubleshooting

### `TclError: is not a valid theme`

Your saved `user_preferences.json` contains a legacy ttkbootstrap 1.x theme name. Delete `user_prefs/user_preferences.json` and restart — M-WAVE will regenerate it with the default theme. Then select a theme from the **Themes** menu.

### `Configuration not found. Cannot run application.`

- Ensure `src/m_wave/assets/configurations/mtl_config.json` is present.
- Verify the JSON file has no syntax errors.
- If running a built executable, confirm your PyInstaller spec includes the `assets/` directory.

### Excel Automation Issues

- Close any open MTL/CMD workbooks before running.
- Confirm Excel is installed and opens normally.

### CSV Encoding Issues

M-WAVE attempts fallback encoding conversion of non-UTF-8 files and may emit a `*_fixed.csv` in the run report folder. If this fails, re-save the CSV as **UTF-8 encoded CSV** from Excel.

### `pip install` fails with "Could not find a version that satisfies the requirement gitleaks"

`gitleaks` is a Go binary (secret scanner), not a PyPI package, and must never appear in `requirements.txt`. Remove it from that file and install it via `scoop install gitleaks` instead.

### `.venv` built against the wrong Python version / mismatched wheels (e.g. `cp311` vs `cp314`)

This happens when `python -m venv .venv` picks up whichever Python resolves first on `PATH`, which can change if you have more than one Python install (e.g. one via the Windows installer, one via Scoop). Delete `.venv` and recreate it with `uv venv --python 3.11 .venv` to pin the interpreter explicitly, then reinstall with `uv pip install ... --python .venv\Scripts\python.exe`.

---

## Project Structure

```
m-wave/
├── pyproject.toml                     # Project metadata and dependency declarations
├── requirements.txt                   # Dev/tooling dependencies (pytest, pyinstaller, etc.)
├── wave.spec                          # PyInstaller build spec
├── generated/                         # Runtime-generated output (gitignored)
│   ├── logs/
│   │   └── <timestamp>_general_error.log
│   └── reports/
│       └── <timestamp>_(<table>_<filter>_<processtype>)/
│           ├── <name>.log
│           └── *.csv
├── user_prefs/                        # Runtime-generated user-editable preferences (gitignored)
│   └── user_preferences.json
├── security_checks                    # Runs the security checking tools automatically.
│   └── security_checks.bat
├── setup                              # Project auto setup and activation.
│   ├── setup.bat
│   ├── setup.sh
│   ├── run.bat
│   └── run.sh
└── src/
    └── m_wave/
        ├── __main__.py                # Entry point — configures logging, launches App
        ├── assets/
        │   ├── configurations/
        │   │   ├── mtl_config.json    # MTL/CMD configuration (bundled with executable)
        │   │   └── user_preferences.json  # Default preferences template
        │   ├── images/
        │   │   ├── logo.ico           # Application icon
        │   │   └── logo.png           # Application png
        │   └── instruction_files/
        │       └── *.txt              # Help text shown via the Help menu
        ├── core/                      # Application-level shared modules
        │   ├── gui.py                 # App (root window), WavePack registration
        │   ├── launcher.py            # LauncherFrame — WavePack selection screen
        │   ├── wavepack_frame.py      # WavePackFrame — base class for all WavePacks
        │   ├── wavepack_controller.py # WavePackController — base controller
        │   ├── context.py             # AppContext — shared runtime state
        │   ├── reporting.py           # Reporting — log/display/modal output routing
        │   ├── paths.py               # AppPaths — PyInstaller-aware path resolution
        │   └── utils.py               # Font/layout constants and shared utilities
        └── wave_packs/
            ├── mtl/                   # Master Tag List WavePack
            │   ├── gui.py             # MTLFrame — MTL WavePack GUI
            │   ├── controller.py      # MTLController, MTLRequest, MTLUi, MTLProcessorType
            │   ├── process.py         # Process — orchestrates compare and append workflows
            │   ├── extraction.py      # DataExtractor — reads MTL tables and input CSVs
            │   ├── formatter.py       # DataFormatter — normalisation, conforming, filtering
            │   ├── comparisons.py     # DataComparator — shape and row-level diff reporting
            │   ├── appender.py        # DataAppender — upsert logic and workbook export
            │   ├── metadata.py        # Metadata, TableType, table formatting rules
            │   └── paths.py           # MTL-specific path constants
            └── example/               # Example WavePack (development example)
                ├── controller.py
                ├── gui.py
                ├── paths.py
                └── process.py
```

---

## License

Internal use only. See [LICENSE](./LICENSE).
