# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH
# This tool was created with the help of AI.

# stdlib
from pathlib import Path

# third-party
# local core
from m_wave.core.paths import PATHS

# Bundled Read-only resources
MTL_INSTRUCTIONS_PATH = PATHS.bundled_instructions_dir / "mtl_instructions.txt"
MTL_CONFIG_TEMPLATE_PATH = PATHS.bundled_configs_dir / "mtl_config.json"

# Extra resources
MTL_DEMO_VIDEO_PATH = PATHS.extras_dir / "mtl_process_demo.mp4"

# Generated/writable MTL folders
MTL_USER_CONFIG_DIR = PATHS.create_sub_folder(
    PATHS.user_config_dir, "mtl-cmd_processor"
)
MTL_DOC_DIR = PATHS.create_sub_folder(MTL_USER_CONFIG_DIR, "stored_documents")
MTL_CONFIG_DIR = PATHS.create_sub_folder(MTL_USER_CONFIG_DIR, "configurations")

# Writable resources
MTL_CONFIG_PATH = MTL_CONFIG_DIR / "mtl_config.json"


def get_mtl_config_path() -> Path:
    """
    Return the writable mtl config path.

    If it does not exist, create it from the bundled template.
    """
    import shutil
    import warnings

    if MTL_CONFIG_PATH.exists():
        return MTL_CONFIG_PATH

    if not MTL_CONFIG_TEMPLATE_PATH.exists():
        warnings.warn(
            f"MTL config template not found at: {MTL_CONFIG_TEMPLATE_PATH}. "
            f"Runtime MTL config could not be initialized at: {MTL_CONFIG_PATH}",
            RuntimeWarning,
            stacklevel=2,
        )
        return MTL_CONFIG_PATH

    try:
        MTL_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy(MTL_CONFIG_TEMPLATE_PATH, MTL_CONFIG_PATH)
        return MTL_CONFIG_PATH
    except Exception as e:
        warnings.warn(
            f"Could not initialize writable MTL config at: {MTL_CONFIG_PATH}. "
            f"Error occurred while initializing MTL config: {e}",
            RuntimeWarning,
            stacklevel=2,
        )
        return MTL_CONFIG_PATH
