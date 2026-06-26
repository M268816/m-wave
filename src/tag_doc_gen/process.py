# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
#
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.tag_doc_gen.controller import TagDocGenRequest

# stdio
from datetime import datetime

# third-party

# local
from src.app.reporting import Reporting
from src.app.utils import DATETIME_FORMAT_MERCK, USER

UA_FILTER_HEADERS = [
    "KepwareTag",
    "NodeId",
    "CustomStreamId",
]

FILTER_FILE_HEADERS = [
    "NodeId",
    "CustomStreamId",
    "SamplingInterval",
    "QueueSize",
    "MonitoringMode",
    "DataChangeTrigger",
    "Deadband",
    "DeadbandType",
]


class Process:
    def __init__(
        self,
        report: Reporting,
        req: TagDocGenRequest,
    ) -> None:
        self.report = report
        self.site = "USJA"
        self.dept = req.department_code.get()
        self.equipment_code = req.equipment_code.get()
        self.kepware_channel = req.kepware_channel.get()
        self.kepware_device = req.kepware_device.get()
        self.namespace_index = req.namespace_index.get()
        self.node_id_prefix = req.node_id_prefix.get()
        self.prefix_len = req.tag_prefix_length.get()
        self.tag_prefix = self.set_tag_prefix()
        self.kepware_prefix = self.set_kepware_prefix()

    def set_tag_prefix(self) -> str:
        lst: list[str] = []
        lst.append(self.site)
        lst.append(self.dept)
        lst.append(self.equipment_code)
        return "_".join(lst) + "_"

    def set_kepware_prefix(self) -> str:
        return (
            self.node_id_prefix + self.kepware_channel + "." + self.kepware_device + "."
        )

    ############
    # PI Attributes to Tags and Config Strings
    ############

    def create_tag(self, pi_attribute: str) -> str:
        return self.tag_prefix + pi_attribute

    def create_config_string(self, pi_attribute: str) -> str:
        return "\\\\%Server%\\%@Tag Prefix%" + pi_attribute

    ############
    # Kepware Tags to UA Filter
    ############

    def create_node_id(self, tag_name: str) -> str:
        return self.kepware_prefix + tag_name

    def create_stream_id(self, tag_name: str) -> str:
        return self.tag_prefix + tag_name

    ############
    # Instrument Tag
    ############

    def create_instrument_tag(self, node_id: str) -> str:
        return node_id[8:]

    def run(self):
        self.report.title("Tag Document Generator")
        merck_datetime = datetime.now().strftime(DATETIME_FORMAT_MERCK)
        self.report.subtitle(f"Started by {USER} on {merck_datetime}")
        self.report.info("This is just a test!")

        self.report.save_report()
