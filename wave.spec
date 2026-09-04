# -*- mode: python ; coding: utf-8 -*-
# m-wave.spec — PyInstaller spec file for WAVE one-file executable
#
# Build command:
#   pyinstaller wave.spec
#
# Output: dist/m-wave.exe  (one-file, no console window)
# The exe will create logs/ and reports/ folders next to itself at runtime.

import os
from PyInstaller.building.build_main import Analysis, PYZ, EXE
from PyInstaller.utils.hooks import collect_data_files

# ── Paths ──────────────────────────────────────────────────────────────────────
# Assumes the spec file lives at the project root
#   m-wave/
ROOT        = os.path.abspath(".")
SRC_DIR     = os.path.join(ROOT, "src")
PACKAGE_DIR = os.path.join(SRC_DIR, "m_wave")
ASSETS_DIR  = os.path.join(PACKAGE_DIR, "assets")
ICON_PATH   = os.path.join(ASSETS_DIR, "images", "logo.ico")

# ── Analysis ───────────────────────────────────────────────────────────────────
a = Analysis(
    # Entry point
    # package engry point lives at src/m_wave/__main__.py
    [os.path.join(PACKAGE_DIR,"__main__.py")],

    # Tell PyInstaller where to look for imports
    pathex=[SRC_DIR],

    # Binary dependencies (.dll / .so).  Add entries here if needed.
    binaries=[],

    # Static files to bundle into the exe's internal _MEIPASS temp folder.
    # This bundles: src/m_wave.assets into sys._MEIPASS/assets
    # paths.py should resolve as: path(sys._MEIPASS) / "assets"

    # paths.py reads these via get_temp_path() / sys._MEIPASS at runtime.
    datas=[
        (ASSETS_DIR, "assets"),
        *collect_data_files("ttkbootstrap"),
        *collect_data_files("datacompy"),
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

        # ── pandas internals ───────────────────────────────────────────────────
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

        # ── openpyxl  ──────────────────────────────────────────────────────────
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

        # ── the wave package ───────────────────────────────────────────────────
        "m_wave.core",

        "m_wave.core.context",
        "m_wave.core.gui",
        "m_wave.core.launcher",
        "m_wave.core.paths",
        "m_wave.core.reporting",
        "m_wave.core.utils",
        "m_wave.core.wavepack_controller",
        "m_wave.core.wavepack_frame",

        "m_wave.wave_packs",

        "m_wave.wave_packs.mtl",
        "m_wave.wave_packs.mtl.appender",
        "m_wave.wave_packs.mtl.comparisons",
        "m_wave.wave_packs.mtl.controller",
        "m_wave.wave_packs.mtl.extraction",
        "m_wave.wave_packs.mtl.formatter",
        "m_wave.wave_packs.mtl.gui",
        "m_wave.wave_packs.mtl.metadata",
        "m_wave.wave_packs.mtl.paths",
        "m_wave.wave_packs.mtl.process",
        "m_wave.wave_packs.mtl.utils",

        "m_wave.wave_packs.tag_doc_gen",
        "m_wave.wave_packs.tag_doc_gen.controller",
        "m_wave.wave_packs.tag_doc_gen.gui",
        "m_wave.wave_packs.tag_doc_gen.metadata",
        "m_wave.wave_packs.tag_doc_gen.paths",
        "m_wave.wave_packs.tag_doc_gen.process",
        "m_wave.wave_packs.tag_doc_gen.utils",

        "m_wave.wave_packs.example",
        "m_wave.wave_packs.example.controller",
        "m_wave.wave_packs.example.gui",
        "m_wave.wave_packs.example.paths",
        "m_wave.wave_packs.example.process",

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

    name="m-wave",

    # ── Appearance ─────────────────────────────────────────────────────────────
    # If logo.png is your only asset, convert it first:
    #   pip install pillow
    #   python -c "from PIL import Image; Image.open('assets/logo.png').save('assets/logo.ico')"

    icon=ICON_PATH,

    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],

    console=False,

    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
