# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
#
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH

# stdlib

# third party

# local
from src.app.utils import USER_PREFS_PATH, load_configs


class AppContext:
    """
    Master application contextualizer. Controls  root/app and User Preferences.
    """

    def __init__(self) -> None:
        self.user_preferences: dict = load_configs(USER_PREFS_PATH)

        # -------------------------------------------------------------------------
        # Possible future context variables #
        # -------------------------------------------------------------------------
        # active_user: str             # who is logged in
        # environment: str             # DEV / VAL / PROD
        # feature_flags: dict          # toggle experimental features
        # session_id: str              # for logging/audit trails
        # license_info: LicenseInfo    # if the app ever gets licensed
        # app_version: str             # centralised, not hardcoded in About window
