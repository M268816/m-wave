# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH
# This tool was created with the help of AI.

# stdlib
from pathlib import Path

# third-party
# local
from m_wave.core.paths import PATHS

_config_doc = "example_config.json"

# Generated/writable tag doc generator folders
EXAMPLE_GENERATED_DIR = PATHS.create_generated_folder("example")
EXAMPLE_CONFIG_DIR = PATHS.create_sub_folder(EXAMPLE_GENERATED_DIR, "configurations")

# Read-only resources
EXAMPLE_INSTRUCTIONS_PATH = PATHS.instruction_files_dir / "example_instructions.txt"
EXAMPLE_CONFIG_TEMPLATE_PATH = PATHS.configurations_dir / _config_doc

# Writable resources
EXAMPLE_CONFIG_PATH = EXAMPLE_CONFIG_DIR / _config_doc


def get_config_path() -> Path:
    """
    Return the writable tag doc generator config path.

    If it does not exist, create it from the bundled template.
    """
    import shutil
    import warnings

    if EXAMPLE_CONFIG_PATH.exists():
        return EXAMPLE_CONFIG_PATH

    if not EXAMPLE_CONFIG_TEMPLATE_PATH.exists():
        warnings.warn(
            f"EXAMPLE config template not found at: {EXAMPLE_CONFIG_TEMPLATE_PATH}. "
            f"Runtime EXAMPLE config could not be initialized at: {EXAMPLE_CONFIG_PATH}",
            RuntimeWarning,
            stacklevel=2,
        )
        return EXAMPLE_CONFIG_PATH

    try:
        EXAMPLE_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy(EXAMPLE_CONFIG_TEMPLATE_PATH, EXAMPLE_CONFIG_PATH)
        return EXAMPLE_CONFIG_PATH
    except Exception as e:
        warnings.warn(
            f"Could not initialize writable EXAMPLE config at: {EXAMPLE_CONFIG_PATH}. "
            f"Error occurred while initializing EXAMPLE config: {e}",
            RuntimeWarning,
            stacklevel=2,
        )
        return EXAMPLE_CONFIG_PATH
