# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
#
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH

# stdlib
import sys
import warnings
from pathlib import Path


class AppPaths:
    def __init__(self) -> None:
        self.base_path = self.get_base_path()
        self.temp_path = self.get_temp_path()

        self.known_bundled_resources = [
            "assets",
        ]

        self.assets_dir = self.get_bundled_resource_path("assets")

        self.logs_dir = self.create_base_folder("logs")
        self.user_prefs_dir = self.create_base_folder("user_prefs")
        self.reports_dir = self.create_base_folder("reports")

    def _ensure_directory(self, path: Path):
        """
        Will create the path if the path does not exist.
        """
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_base_path(self) -> Path:
        """
        Returns the directory where the exe is located.
        """
        if getattr(sys, "frozen", False):
            # If app is running as a compiled executable
            return Path(sys.executable).parent
        else:
            # App is running as a script or in development
            # NOTE: project root is three levels up from source as: wave/src/app
            return Path(__file__).parent.parent.parent

    def get_temp_path(self) -> Path:
        """
        Returns PyInstaller's temp extraction folder for onefile exe
        or the regular base path if run as script or in dev.
        """
        if getattr(sys, "frozen", False):
            return Path(sys._MEIPASS)  # type: ignore
        else:
            return self.get_base_path()

    def get_bundled_resource_path(self, resource_name: str) -> Path:
        """
        Gets the path of a bundled resource folder (assets, configs, etc.)
        """
        if resource_name not in self.known_bundled_resources:
            warnings.warn(
                "Resource folder name not known. Attempting GET anyway.",
                RuntimeWarning,
                stacklevel=2,
            )
        return self.temp_path / resource_name

    def create_base_folder(self, folder_name: str) -> Path:
        """
        Creates a new folder at the base directory next to the exe.
        """
        new_path = self.base_path / folder_name
        new_folder = self._ensure_directory(new_path)
        return new_folder

    def create_sub_folder(self, parent_folder: Path, folder_name: str) -> Path:
        """
        Creates a new sub-folder from an existing directory.
        """
        new_path = parent_folder / folder_name
        new_folder = self._ensure_directory(new_path)
        return new_folder


# Create the Paths object here, the rest of the app should use this.
PATHS = AppPaths()


# # LEGACY FOR COMPAT
# # BASE_DIR = PATHS.base_path
# TEMP_DIR = PATHS.temp_path
#
# ASSETS_DIR = PATHS.assets_dir
# LOGS_DIR = PATHS.logs_dir
# REPORTS_DIR = PATHS.reports_dir
#
# LOGO_PATH = PATHS.assets_dir / "logo.png"
#
# MTL_INSTRUCTIONS_PATH = PATHS.assets_dir / "mtl_instructions.txt"
# TAG_DOC_GEN_INSTRUCTIONS_PATH = PATHS.assets_dir / "tag_doc_gen_instructions.txt"
# EXAMPLE_INSTRUCTIONS_PATH = PATHS.assets_dir / "example_instructions.txt"
# KEPWARE_COMPARISON_INSTRUCTIONS_PATH = (
#     PATHS.assets_dir / "kepware_comparison_instructions.txt"
# )
#
# # Move to MTL UTILS
# MTL_CONFIG_PATH = PATHS.assets_dir / "mtl_config.json"
# # USER_PREFS_PATH = get_user_prefs(APP_DIRS)
