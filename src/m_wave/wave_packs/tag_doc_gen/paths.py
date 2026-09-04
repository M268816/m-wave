# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
#
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH

# stdlib
from pathlib import Path

# third-party

# local
from m_wave.core.paths import PATHS

# Generated/writable tag doc generator folders
TDG_GENERATED_DIR = PATHS.create_generated_folder("tag_doc_gen")
TDG_CONFIG_DIR = PATHS.create_sub_folder(TDG_GENERATED_DIR, "configurations")

# Read-only resources
TDG_INSTRUCTIONS_PATH = PATHS.instruction_files_dir / "tag_doc_gen.txt"
TDG_CONFIG_TEMPLATE_PATH = PATHS.configurations_dir / "tdg_config.json"

# Writable resources
TDG_CONFIG_PATH = TDG_CONFIG_DIR / "tdg_config.json"


def get_config_path() -> Path:
    """
    Return the writable tag doc generator config path.

    If it does not exist, create it from the bundled template.
    """
    import shutil
    import warnings

    if TDG_CONFIG_PATH.exists():
        return TDG_CONFIG_PATH

    if not TDG_CONFIG_TEMPLATE_PATH.exists():
        warnings.warn(
            f"TDG config template not found at: {TDG_CONFIG_TEMPLATE_PATH}. "
            f"Runtime TDG config could not be initialized at: {TDG_CONFIG_PATH}",
            RuntimeWarning,
            stacklevel=2,
        )
        return TDG_CONFIG_PATH

    try:
        TDG_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy(TDG_CONFIG_TEMPLATE_PATH, TDG_CONFIG_PATH)
        return TDG_CONFIG_PATH
    except Exception as e:
        warnings.warn(
            f"Could not initialize writable TDG config at: {TDG_CONFIG_PATH}. "
            f"Error occurred while initializing TDG config: {e}",
            RuntimeWarning,
            stacklevel=2,
        )
        return TDG_CONFIG_PATH
