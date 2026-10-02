# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH
# This tool was created with the help of AI.

# stdlib
import sys
import warnings
from pathlib import Path


class AppPaths:
    def __init__(self) -> None:
        self.project_root = self.get_project_root()
        self.package_root = self.get_package_root()
        self.exe_dir = self.get_exe_dir()
        self.resource_root = self.get_resource_root()
        self.folder_generation_root = self.get_folder_generation_root()

        self.known_bundled_resources = [
            "assets",
            "configurations",
            "images",
            "instruction_files",
        ]

        # Bundled/read-only resources
        self.bundled_assets_dir = self.resource_root / "assets"
        self.bundled_configs_dir = self.bundled_assets_dir / "configurations"
        self.bundled_images_dir = self.bundled_assets_dir / "images"
        self.bundled_instructions_dir = self.bundled_assets_dir / "instruction_files"

        # External resource folders
        # This folder shall only contain artifacts when packaged with the built
        # executable. For example, the MTL Demo video should not be included with
        # a onefile executable, as the startup time would greatly decrease. So,
        # large files should be packaged with the exe build in the zipped distribution
        # instead. This resource folder generated here is that "external" folder.
        self.extras_dir = self.get_external_folder("extras")

        # Generated/writable folders
        self.logs_dir = self.create_generated_folder("logs")
        self.reports_dir = self.create_generated_folder("reports")
        self.user_preferences_dir = self.create_generated_folder("user_prefs")
        self.user_config_dir = self.create_generated_folder("user_config")

        # Generated/writable files
        self.user_preferences_path = self.user_preferences_dir / "user_preferences.json"

        # Common files
        self.logo_path = self.bundled_images_dir / "logo.png"
        self.user_preferences_template_path = (
            self.bundled_configs_dir / "user_preferences.json"
        )

    @property
    def is_frozen(self) -> bool:
        """
        Returns true when running as a bundled executable from PyInstaller
        """
        return getattr(sys, "frozen", False)

    def _ensure_directory(self, path: Path):
        """
        Will create the path if the path does not exist.
        """
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_project_root(self) -> Path:
        """
        Returns the project root during development.
        Assumes the file is located at:
            m-wave/src/m_wave/core/paths.py
        This means:
            resolve().parents[0] = ./src/m_wave/core
            resolve().parents[1] = ./src/m_wave
            resolve().parents[2] = ./src
            resolve().parents[3] = ./m-wave
        """
        if self.is_frozen:
            # If app is running as a compiled executable
            return self.get_exe_dir()

        # Otherwise app is running in development
        # and needs to be resolved at ./m-wave
        return Path(__file__).resolve().parents[3]  # ./m-wave

    def get_package_root(self) -> Path:
        """
        Returns the python package root during development.
        Development:
            m-wave/src/m_wave
        Frozen:
            Usually not meaningful as a source package path, so use resource root.
        """
        if self.is_frozen:
            return self.get_resource_root()

        return Path(__file__).resolve().parents[1]  # ./m-wave/src/m_wave

    def get_exe_dir(self) -> Path:
        """
        Returns the folder containing the executable when froze,
        or the project root when in development.
        """
        if self.is_frozen:
            return Path(sys.executable).resolve().parent

        return self.get_project_root()

    def get_resource_root(self) -> Path:
        """
        Return the root location for bundled resources.
        Returns PyInstaller's temp extraction folder for onefile exe
        or the regular base path if run as script or in dev.
        """
        if self.is_frozen:
            return Path(sys._MEIPASS)  # type: ignore

        return self.get_package_root()

    def get_folder_generation_root(self) -> Path:
        """
        Returns the root folder for the generated files.
        Development:
            ./m-wave/generated
        Production:
            The folder the exe lives in.
        """
        if self.is_frozen:
            return self.get_exe_dir()

        return self.get_project_root() / "generated"

    def get_bundled_resource_path(self, resource_name: str) -> Path:
        """
        Gets the path of a bundled resource folder (assets, configs, etc.)
        """
        if resource_name not in self.known_bundled_resources:
            warnings.warn(
                f"Resource name {resource_name} is not registered. "
                + "Attempting to resolve anyway.",
                RuntimeWarning,
                stacklevel=2,
            )

        return self.resource_root / resource_name

    def create_generated_folder(self, folder_name: str) -> Path:
        """
        Creates a generated/writable folder.
        Development:
            ./m-wave/generated/<folder_name>
        Production:
            exe-folder/<folder_name>
        """
        new_path = self.folder_generation_root / folder_name
        return self._ensure_directory(new_path)

    def create_sub_folder(self, parent_folder: Path, folder_name: str) -> Path:
        """
        Creates a new sub-folder from an existing directory.
        """
        new_path = parent_folder / folder_name
        new_folder = self._ensure_directory(new_path)
        return new_folder

    def get_external_folder(self, folder_name: str) -> Path:
        """
        Returns an external folder.
        Returns in build: ./exe_folder/external
        Returns in dev: ./m_wave/assets/external
        """
        if self.is_frozen:
            return self._ensure_directory(self.exe_dir / folder_name)
        return self._ensure_directory(self.bundled_assets_dir / folder_name)


# Create the Paths object here, the rest of the app should use this.
PATHS = AppPaths()
