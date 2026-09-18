#  Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
#
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH

# stdlib
import json

# local core
from m_wave.core.reporting import Reporting

# local wave pack
from m_wave.wave_packs.tag_doc_gen.paths import get_config_path


class Metadata:
    def __init__(self, report: Reporting, ws_name: str | None = None) -> None:
        self.report: Reporting = report
        self.tdg_configs = self.get_configs()

    def get_configs(self) -> dict:
        try:
            with open(get_config_path(), "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            raise SystemExit(f"Configuration not found. Cannot run application.\n{e}")

    def get_ua_filter_headers(self) -> list:
        return self.tdg_configs["UA_FILTER_HEADERS"]

    def get_filter_file_headers(self) -> list:
        return self.tdg_configs["FILTER_FILE_HEADERS"]

    def get_tag_to_attribute_headers(self) -> list:
        return self.tdg_configs["TAG_TO_ATTRIBUTE_HEADERS"]

    def get_kepware_to_pi_headers(self) -> list:
        return self.tdg_configs["KEPWARE_TO_PI_HEADERS"]

    def get_kepware_to_pi_defaults(self) -> dict:
        return self.tdg_configs["KEPWARE_TO_PI_DEFAULTS"]

    def get_kepware_to_pi_auto_inputs(self) -> dict:
        return self.tdg_configs["KEPWARE_TO_PI_AUTO_INPUTS"]

    def get_pi_data_conversion_map(self) -> dict:
        return self.tdg_configs["PI_DATA_CONVERSION_MAP"]

    def get_kepware_data_conversion_map(self) -> dict:
        return self.tdg_configs["KEPWARE_DATA_CONVERSION_MAP"]

    def get_lookup_keys(self) -> list:
        return self.tdg_configs["LOOKUP_KEYS"]

    def get_kepware_export_headers(self) -> list:
        return self.tdg_configs["KEPWARE_EXPORT_HEADERS"]
