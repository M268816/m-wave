<<<<<<< HEAD
<p align="center">
  <img src="src/m_wave/assets/images/logo.png" alt="M-WAVE logo" width="140" />
</p>

<h1 align="center">M-WAVE</h1>
<p align="center"><strong>Workbook Automation &amp; Verification Engine</strong></p>

<p align="center">
  <img alt="Version" src="https://img.shields.io/badge/version-0.1.0--dev.6-blue" />
  <img alt="Python" src="https://img.shields.io/badge/python-3.11%2B-blue" />
  <img alt="Platform" src="https://img.shields.io/badge/platform-Windows-lightgrey" />
  <a href="http://157.93.24.68/M268816/WAVE/issues">
    <img alt="Issues" src="https://img.shields.io/badge/issues-Gitea-green" />
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

_Planned_

- **MES**

### Outputs

M-WAVE writes artifacts next to the executable (or project root when running from source):

- `generated/reports/` — per-run report folders named `TIMESTAMP_(table_filter_processtype)/` containing:
  - `*.log` run report
  - CSV snapshots/exports (see below)
  - Appended workbook copy (append workflow only)
- `generated/logs/` — general application error logs
- `user_prefs/` — persisted user preferences

Common per-run CSV artifacts:

| Workflow  | File                                                                        |
| --------- | --------------------------------------------------------------------------- |
| Append    | `mtl_dataframe_before.csv`, `input_dataframe.csv`, `mtl_dataframe_after.csv` |
| Compare   | `rows_only_within_MTL.csv`, `rows_only_within_input.csv`, `*_comparison.csv`, `comparable_rows.csv`, `non_comparable_rows.csv` |

---

## Important Notes / Assumptions

- **Close any MTL/CMD workbook before running M-WAVE.** M-WAVE automates Excel via `xlwings`.
- M-WAVE is tested against a specific MTL/CMD version defined in `src/m_wave/assets/configurations/mtl_config.json` (see `"mtl_version"`).
- For append workflows, **do not pre-populate a `Version` column** in the input CSV — M-WAVE manages this during column conformance.
- **Do not change configurations or report options while a process is running.** M-WAVE will reject the change and restore the previous value.
- **Do not close M-WAVE while a process is running.** A confirmation dialog will warn you — any in-progress work will be lost.

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

---

## How It Works (MTL Example)

1. Launch M-WAVE — the **WavePack Launcher** is shown.
2. Select a WavePack (e.g. **Master Tag List Processor**). You are locked into your WavePack for the session; restart to change.
3. Select files:
   - MTL/CMD workbook (`.xlsx` / `.xlsm`)
   - PI Builder export (`.csv`) — or use **Import** to download the latest MTL from the web
4. Choose a target **MTL/CMD table** from the dropdown (mappings come from `mtl_config.json`)
5. Optionally enter a **Filter** string (applied to configured filter columns; some tables use key-based filtering)
6. Select a process type:
   - **Compare** — validate differences between selected files
   - **Append** — upsert and generate an updated workbook copy
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

- Python **3.11+**
- Microsoft Excel installed (required for `xlwings` automation)
- Windows

### Quick Start

Use the included `setup.bat` to create the virtual environment and install dependencies, then `run.bat` to launch:

```bat
setup.bat
run.bat
```

### Manual Setup

```bat
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -e .
```

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
pip install pyinstaller
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

---

## Project Structure

```
m-wave/
├── setup.bat                          # Creates venv and installs dependencies
├── run.bat                            # Activates venv and launches M-WAVE
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
├── user_prefs/                        # User-editable preferences (auto-generated)
│   └── user_preferences.json
└── src/
    └── m_wave/
        ├── __main__.py                # Entry point — configures logging, launches App
        ├── assets/
        │   ├── configurations/
        │   │   ├── mtl_config.json    # MTL/CMD configuration (bundled with executable)
        │   │   └── user_preferences.json  # Default preferences template
        │   ├── images/
        │   │   └── logo.png           # Application icon
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
            └── example/               # Example WavePack (dev/testing placeholder)
                └── gui.py             # ExampleFrame
```

---

## License

Internal use only. See [LICENSE](./LICENSE).

## Repositories

This project is hosted on both **GitHub** and **Gitea**. Consult the M-WAVE SOP for repository access details.
=======
# m-wave



## Getting started

To make it easy for you to get started with GitLab, here's a list of recommended next steps.

Already a pro? Just edit this README.md and make it your own. Want to make it easy? [Use the template at the bottom](#editing-this-readme)!

## Add your files

- [ ] [Create](https://docs.gitlab.com/ee/user/project/repository/web_editor.html#create-a-file) or [upload](https://docs.gitlab.com/ee/user/project/repository/web_editor.html#upload-a-file) files
- [ ] [Add files using the command line](https://docs.gitlab.com/ee/gitlab-basics/add-file.html#add-a-file-using-the-command-line) or push an existing Git repository with the following command:

```
cd existing_repo
git remote add origin https://gitlab-ce.merckgroup.com/jaffreydatasystems/m-wave.git
git branch -M main
git push -uf origin main
```

## Integrate with your tools

- [ ] [Set up project integrations](https://gitlab-ce.merckgroup.com/jaffreydatasystems/m-wave/-/settings/integrations)

## Collaborate with your team

- [ ] [Invite team members and collaborators](https://docs.gitlab.com/ee/user/project/members/)
- [ ] [Create a new merge request](https://docs.gitlab.com/ee/user/project/merge_requests/creating_merge_requests.html)
- [ ] [Automatically close issues from merge requests](https://docs.gitlab.com/ee/user/project/issues/managing_issues.html#closing-issues-automatically)
- [ ] [Enable merge request approvals](https://docs.gitlab.com/ee/user/project/merge_requests/approvals/)
- [ ] [Set auto-merge](https://docs.gitlab.com/ee/user/project/merge_requests/merge_when_pipeline_succeeds.html)

## Test and Deploy

Use the built-in continuous integration in GitLab.

- [ ] [Get started with GitLab CI/CD](https://docs.gitlab.com/ee/ci/quick_start/index.html)
- [ ] [Analyze your code for known vulnerabilities with Static Application Security Testing (SAST)](https://docs.gitlab.com/ee/user/application_security/sast/)
- [ ] [Deploy to Kubernetes, Amazon EC2, or Amazon ECS using Auto Deploy](https://docs.gitlab.com/ee/topics/autodevops/requirements.html)
- [ ] [Use pull-based deployments for improved Kubernetes management](https://docs.gitlab.com/ee/user/clusters/agent/)
- [ ] [Set up protected environments](https://docs.gitlab.com/ee/ci/environments/protected_environments.html)

***

# Editing this README

When you're ready to make this README your own, just edit this file and use the handy template below (or feel free to structure it however you want - this is just a starting point!). Thanks to [makeareadme.com](https://www.makeareadme.com/) for this template.

## Suggestions for a good README

Every project is different, so consider which of these sections apply to yours. The sections used in the template are suggestions for most open source projects. Also keep in mind that while a README can be too long and detailed, too long is better than too short. If you think your README is too long, consider utilizing another form of documentation rather than cutting out information.

## Name
Choose a self-explaining name for your project.

## Description
Let people know what your project can do specifically. Provide context and add a link to any reference visitors might be unfamiliar with. A list of Features or a Background subsection can also be added here. If there are alternatives to your project, this is a good place to list differentiating factors.

## Badges
On some READMEs, you may see small images that convey metadata, such as whether or not all the tests are passing for the project. You can use Shields to add some to your README. Many services also have instructions for adding a badge.

## Visuals
Depending on what you are making, it can be a good idea to include screenshots or even a video (you'll frequently see GIFs rather than actual videos). Tools like ttygif can help, but check out Asciinema for a more sophisticated method.

## Installation
Within a particular ecosystem, there may be a common way of installing things, such as using Yarn, NuGet, or Homebrew. However, consider the possibility that whoever is reading your README is a novice and would like more guidance. Listing specific steps helps remove ambiguity and gets people to using your project as quickly as possible. If it only runs in a specific context like a particular programming language version or operating system or has dependencies that have to be installed manually, also add a Requirements subsection.

## Usage
Use examples liberally, and show the expected output if you can. It's helpful to have inline the smallest example of usage that you can demonstrate, while providing links to more sophisticated examples if they are too long to reasonably include in the README.

## Support
Tell people where they can go to for help. It can be any combination of an issue tracker, a chat room, an email address, etc.

## Roadmap
If you have ideas for releases in the future, it is a good idea to list them in the README.

## Contributing
State if you are open to contributions and what your requirements are for accepting them.

For people who want to make changes to your project, it's helpful to have some documentation on how to get started. Perhaps there is a script that they should run or some environment variables that they need to set. Make these steps explicit. These instructions could also be useful to your future self.

You can also document commands to lint the code or run tests. These steps help to ensure high code quality and reduce the likelihood that the changes inadvertently break something. Having instructions for running tests is especially helpful if it requires external setup, such as starting a Selenium server for testing in a browser.

## Authors and acknowledgment
Show your appreciation to those who have contributed to the project.

## License
For open source projects, say how it is licensed.

## Project status
If you have run out of energy or time for your project, put a note at the top of the README saying that development has slowed down or stopped completely. Someone may choose to fork your project or volunteer to step in as a maintainer or owner, allowing your project to keep going. You can also make an explicit request for maintainers.
>>>>>>> gitlab/main
