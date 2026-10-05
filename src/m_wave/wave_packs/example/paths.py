# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH
# This tool was created with the help of AI.

# stdlib
from pathlib import Path

# third-party
# local
from m_wave.core.paths import PATHS

_instructions_doc = "example_instructions.txt"
_config_doc = "example_config.json"

# Bundled read-only resources
BUNDLED_INSTRUCTIONS_PATH = PATHS.bundled_instructions_dir / _instructions_doc
BUNDLED_CONFIG_TEMPLATE_PATH = PATHS.bundled_configs_dir / _config_doc

# Core writable folders
USER_CONFIG_DIR = PATHS.create_sub_folder(PATHS.user_config_dir, "example")

# Extra folder
# This path is to be used for large files that should not be bundled in the exe.
# After building, extra files should be included with the zipped package within
# an "extras" folder. Below is an example of a large file that should not be built
# within the EXE. This files does not actually exist, so don't try to test it.

# EXTRA_DIR = PATHS.extras_dir
# EXAMPLE_BIG_FILE_PATH = EXTRA_DIR / "8k_paris_panarama.png"

# WavePack writeable folders
EXAMPLE_WRITABLE_DIR = PATHS.create_generated_folder("example_of_new_directory")

# WavePack writable resources
USER_CONFIG_PATH = USER_CONFIG_DIR / _config_doc


def get_config_path() -> Path:
    """
    Return the writable configuration path.

    If it does not exist, create it from the bundled template.
    """
    import shutil
    import warnings

    if USER_CONFIG_PATH.exists():
        return USER_CONFIG_PATH

    if not BUNDLED_CONFIG_TEMPLATE_PATH.exists():
        warnings.warn(
            "This WavePack's configuration template was not found at: "
            f"{BUNDLED_CONFIG_TEMPLATE_PATH}. "
            "The user configuration file could not be initialized at: "
            f"{USER_CONFIG_PATH}",
            RuntimeWarning,
            stacklevel=2,
        )
        return USER_CONFIG_PATH

    try:
        USER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy(BUNDLED_CONFIG_TEMPLATE_PATH, USER_CONFIG_PATH)
        return USER_CONFIG_PATH
    except Exception as e:
        warnings.warn(
            "There was a problem initializing this WavePack's configuration file at: "
            f"{USER_CONFIG_PATH}. "
            f"The error occurred while attempting to initialize '{_config_doc}': {e}",
            RuntimeWarning,
            stacklevel=2,
        )
        return USER_CONFIG_PATH
