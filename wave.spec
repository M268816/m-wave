# -*- mode: python ; coding: utf-8 -*-
# wave.spec — PyInstaller spec file for WAVE one-file executable
#
# Build command:
#   pyinstaller wave.spec
#
# Output: dist/wave.exe  (one-file, no console window)
# The exe will create logs/ and reports/ folders next to itself at runtime.

import os
from PyInstaller.building.build_main import Analysis, PYZ, EXE

# ── Paths ──────────────────────────────────────────────────────────────────────
# Assumes the spec file lives at the project root (wave/)
ROOT       = os.path.abspath(".")
ASSETS_DIR = os.path.join(ROOT, "assets")

# ── Analysis ───────────────────────────────────────────────────────────────────
a = Analysis(
    # Entry point — main.py lives inside src/
    [os.path.join(ROOT, "src", "main.py")],

    # Tell PyInstaller where to look for imports
    pathex=[ROOT],

    # Binary dependencies (.dll / .so).  Add entries here if needed.
    binaries=[],

    # Static files to bundle into the exe's internal _MEIPASS temp folder.
    # Format: (absolute_source_path, destination_folder_inside_bundle)
    # paths.py reads these via get_temp_path() / sys._MEIPASS at runtime.
    datas=[
        (os.path.join(ASSETS_DIR, "config.json"),       "assets"),
        (os.path.join(ASSETS_DIR, "logo.png"),           "assets"),
        (os.path.join(ASSETS_DIR, "instructions.txt"),   "assets"),
    ],

    # Modules PyInstaller cannot detect automatically (dynamic imports, etc.)
    hiddenimports=[
        # ── tkinter ────────────────────────────────────────────────────────────
        "tkinter",
        "tkinter.ttk",
        "tkinter.messagebox",
        "tkinter.filedialog",
        "tkinter.scrolledtext",
        # ── ttkbootstrap ───────────────────────────────────────────────────────
        "ttkbootstrap",
        "ttkbootstrap.dialogs",
        "ttkbootstrap.constants",
        "ttkbootstrap.style",
        "ttkbootstrap.themes",
        # ── pandas internals (commonly missed by the hook) ─────────────────────
        "pandas",
        "pandas._libs.tslibs.base",
        "pandas._libs.tslibs.nattype",
        "pandas._libs.tslibs.np_datetime",
        "pandas._libs.tslibs.timedeltas",
        "pandas._libs.tslibs.timestamps",
        "pandas._libs.tslibs.offsets",
        "pandas._libs.tslibs.period",
        "pandas._libs.tslibs.strptime",
        "pandas._libs.tslibs.vectorized",
        "pandas._libs.window.aggregations",
        "pandas._libs.window.indexers",
        "pandas.core.arrays.string_",
        "pandas.io.formats.style",
        # ── openpyxl (PyInstaller hook misses several sub-modules) ─────────────
        "openpyxl",
        "openpyxl.styles",
        "openpyxl.styles.differential",
        "openpyxl.styles.numbers",
        "openpyxl.utils",
        "openpyxl.utils.dataframe",
        "openpyxl.workbook",
        "openpyxl.reader.excel",
        "openpyxl.writer.excel",
        "openpyxl.chart",
        "openpyxl.chart.label",
        # ── xlwings ────────────────────────────────────────────────────────────
        "xlwings",
        # ── numpy ──────────────────────────────────────────────────────────────
        "numpy",
        "numpy.core._methods",
        "numpy.lib.format",
        # ── your src package ───────────────────────────────────────────────────
        "src",
        "src.mtl.appender",
        "src.mtl.comparator",
        "src.mtl.extraction",
        "src.mtl.formatter",
        "src.mtl.process",
        "src.controllers",
        "src.gui",
        "src.metadata",
        "src.paths",
        "src.reporting",
    ],

    hookspath=[],
    runtime_hooks=[],

    # Trim the exe by excluding packages you never use
    excludes=[
        "matplotlib",
        "scipy",
        "IPython",
        "notebook",
        "pytest",
        "_pytest",
        "setuptools",
        "pkg_resources",
        "xmlrunner",
    ],

    cipher=None,
    noarchive=False,
)

# ── PYZ ────────────────────────────────────────────────────────────────────────
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# ── EXE ────────────────────────────────────────────────────────────────────────
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],

    name="wave",

    # ── Appearance ─────────────────────────────────────────────────────────────
    icon=os.path.join(ASSETS_DIR, "logo.png"),
    # NOTE: PyInstaller requires a .ico file for the exe icon on Windows.
    # If logo.png is your only asset, convert it first:
    #   pip install pillow
    #   python -c "from PIL import Image; Image.open('assets/logo.png').save('assets/logo.ico')"
    # Then change the line above to: icon=os.path.join(ASSETS_DIR, "logo.ico")

    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],

    console=False,
    onefile=True,

    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
