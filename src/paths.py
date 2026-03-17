# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
#
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH

# stdlib
import sys
from pathlib import Path


def get_base_path() -> Path:
    """
    Get the directory where the .exe is located
    """
    if getattr(sys, "frozen", False):
        # Running as compiled executable
        return Path(sys.executable).parent
    else:
        # Running as script - project root is one level up from src/
        return Path(__file__).parent.parent


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
    base = get_temp_path()
    return base / relative_path


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
        "base": base,
        "logs": ensure_directory(get_data_path("logs")),
        "reports": ensure_directory(get_data_path("reports")),
        "assets": temp / "assets",
        "temp": temp,
    }


# Convenience constants
APP_DIRS = get_app_directories()
BASE_DIR = APP_DIRS["base"]
LOGS_DIR = APP_DIRS["logs"]
REPORTS_DIR = APP_DIRS["reports"]
ASSETS_DIR = APP_DIRS["assets"]
CONFIG_PATH = ASSETS_DIR / "config.json"
TEMP_DIR = APP_DIRS["temp"]
