# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
#
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH

# stdlib
import sys
import json
import warnings
from pathlib import Path


def get_base_path() -> Path:
    """
    Get the directory where the .exe is located
    """
    if getattr(sys, "frozen", False):
        # Running as compiled executable
        return Path(sys.executable).parent
    else:
        # Running as script - project root is two levels up from src/
        # paths lives two levels up in src/app/
        return Path(__file__).parent.parent.parent


def get_temp_path() -> Path:
    """
    Get PyInstaller's temp extraction folder
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)  # type: ignore
    else:
        return get_base_path()


def get_resource_path(relative_path: str) -> Path:
    """
    Get path to bundled resource (assets, config, etc.)
    """
    temp = get_temp_path()
    return temp / relative_path


def get_data_path(relative_path: str) -> Path:
    """
    Get path for user data (logs, reports) next to .exe
    """
    base = get_base_path()
    return base / relative_path


def ensure_directory(path: Path) -> Path:
    """
    Create directory if it doesn't exist
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_app_directories() -> dict[str, Path]:
    """
    Get all application directories
    """
    base = get_base_path()
    temp = get_temp_path()

    return {
        "assets": get_resource_path("assets"),
        "base": base,
        "logs": ensure_directory(get_data_path("logs")),
        "user_prefs": ensure_directory(get_data_path("user_prefs")),
        "reports": ensure_directory(get_data_path("reports")),
        "temp": temp,
    }


def get_user_prefs(_dirs: dict[str, Path]) -> Path:
    """
    Returns the user preferences path. If the user preferences do not exist,
    it creates them form the default assets.
    """
    user_prefs_path = _dirs["user_prefs"] / "user_preferences.json"
    if user_prefs_path.exists():
        return user_prefs_path

    default_path = _dirs["assets"] / "user_preferences.json"

    if default_path.exists():
        with open(default_path, "r", encoding="utf-8") as f:
            default_prefs = json.load(f)

        with open(user_prefs_path, "w", encoding="utf-8") as f:
            json.dump(default_prefs, f, indent=2)
    else:
        warnings.warn(
            "Could not create a user preferences path! Using defaults, but cannot save user settings.",
            RuntimeWarning,
            stacklevel=2,
        )
        return default_path

    return user_prefs_path


# Convenience constants
APP_DIRS = get_app_directories()
BASE_DIR = APP_DIRS["base"]
TEMP_DIR = APP_DIRS["temp"]

ASSETS_DIR = APP_DIRS["assets"]
LOGS_DIR = APP_DIRS["logs"]
REPORTS_DIR = APP_DIRS["reports"]

LOGO_PATH = ASSETS_DIR / "logo.png"

MTL_CONFIG_PATH = ASSETS_DIR / "mtl_config.json"
USER_PREFS_PATH = get_user_prefs(APP_DIRS)

MTL_INSTRUCTIONS_PATH = ASSETS_DIR / "mtl_instructions.txt"
KEPWARE_COMPARISON_INSTRUCTIONS_PATH = (
    ASSETS_DIR / "kepware_comparison_instructions.txt"
)
TAG_DOC_GEN_INSTRUCTIONS_PATH = ASSETS_DIR / "tag_doc_gen_instructions.txt"
EXAMPLE_INSTRUCTIONS_PATH = ASSETS_DIR / "example_instructions.txt"
