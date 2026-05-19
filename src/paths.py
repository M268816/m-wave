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
        "config": ensure_directory(get_data_path("config")),
        "assets": temp / "assets",
        "temp": temp,
    }


def get_config_path(_dirs: dict[str, Path]) -> Path:
    """
    Returns the configuration path. If the user configuration does not exist,
    it creates it from the default assets.
    """
    user_config_path = _dirs["config"] / "config.json"
    if user_config_path.exists():
        return user_config_path

    default_path = _dirs["assets"] / "config.json"

    if default_path.exists():

        with open(default_path, "r", encoding="utf-8") as f:
            default_config = json.load(f)

        with open(user_config_path, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=2)

    else:
        warnings.warn(
            "Could not create a user configuraion path! Using defaults, but cannot save user settings.",
            RuntimeWarning,
            stacklevel=2,
        )
        return default_path

    return user_config_path


# Convenience constants
APP_DIRS = get_app_directories()
BASE_DIR = APP_DIRS["base"]
LOGS_DIR = APP_DIRS["logs"]
REPORTS_DIR = APP_DIRS["reports"]
ASSETS_DIR = APP_DIRS["assets"]
CONFIG_PATH = get_config_path(APP_DIRS)
LOGO_PATH = ASSETS_DIR / "logo.png"
INSTRUCTIONS_PATH = ASSETS_DIR / "instructions.txt"
TEMP_DIR = APP_DIRS["temp"]
