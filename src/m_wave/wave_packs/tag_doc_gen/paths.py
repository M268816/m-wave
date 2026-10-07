# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
#
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH

# stdlib
from pathlib import Path

# third-party
# local
from m_wave.core.paths import PATHS

_instructions_doc = "tdg_instructions.txt"
_config_doc = "tdg_config.json"

# Bunlded read-only resources
BUNDLED_INSTRUCTIONS_PATH = PATHS.bundled_instructions_dir / _instructions_doc
BUNDLED_CONFIG_TEMPLATE_PATH = PATHS.bundled_configs_dir / _config_doc

# Extra folder
# EXTRA_DIR = PATHS.extra_dir
# EXAMPLE_EXTRA_FILE = EXTRA_DIR / "16k_panorama.png"

# Core Writeable Folders
TDG_USER_CONFIG_DIR = PATHS.create_sub_folder(
    PATHS.user_config_dir, "pi_tag_doc_generator"
)

# Writable resources
TDG_CONFIG_PATH = TDG_USER_CONFIG_DIR / _config_doc


def get_config_path() -> Path:
    """
    Return the writable tag doc generator config path.

    If it does not exist, create it from the bundled template.
    """
    import shutil
    import warnings

    if TDG_CONFIG_PATH.exists():
        return TDG_CONFIG_PATH

    if not BUNDLED_CONFIG_TEMPLATE_PATH.exists():
        warnings.warn(
            f"TDG configuration template not found at: {BUNDLED_CONFIG_TEMPLATE_PATH}. "
            f"Runtime TDG config could not be initialized at: {TDG_CONFIG_PATH}",
            RuntimeWarning,
            stacklevel=2,
        )
        return TDG_CONFIG_PATH

    try:
        TDG_USER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy(BUNDLED_CONFIG_TEMPLATE_PATH, TDG_CONFIG_PATH)
        return TDG_CONFIG_PATH
    except FileNotFoundError as e:
        warnings.warn(
            f"Could not initialize writable TDG config at: {TDG_CONFIG_PATH}. "
            f"Error occurred while initializing '{_config_doc}': {e}",
            RuntimeWarning,
            stacklevel=2,
        )
        return TDG_CONFIG_PATH
