# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
#
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.tag_formatter.controller import TagFormatterRequest, TagFormatterUi

# stdio

# third-party
import pandas as pd

# local
from src.app.reporting import Reporting

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


class TagBuilder:
    def __init__(
        self,
        req: TagFormatterRequest,
    ) -> None:
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


class TagFormatterProcess:
    def __init__(
        self, report: Reporting, req: TagFormatterRequest, ui: TagFormatterUi
    ) -> None:
        self.report = report
        self.tag_builder = TagBuilder(req)
        self.plc_tags = ""  # This needs to be a CSV import.
        self.kepware_tags = ""  # This needs to be a CSV import

    def run(self) -> None:
        self.report.debug("Testing", popup=True)


if __name__ == "__main__":
    import ttkbootstrap as tkb
    from src.tag_formatter.controller import TagProcessorType, TagFormatterRequest

    app = tkb.Window()

    req = TagFormatterRequest(
        equipment_code=tkb.StringVar(value="FC01"),
        kepware_channel=tkb.StringVar(value="MB000"),
        kepware_device=tkb.StringVar(value="DRTSTDC"),
        department_code=tkb.StringVar(value="EXP"),
        tag_prefix_length=tkb.StringVar(value="15"),
        node_id_prefix=tkb.StringVar(value="ns=2;s="),
        namespace_index=tkb.StringVar(value="2"),
        processor_type=TagProcessorType.KEPWARE_TO_FILTER,
    )

    tag_name = "Lot_Number"
    pi_attribute = "Axis01.Temp"

    b = TagBuilder(req=req)

    t = b.create_config_string(pi_attribute)
    print(t)

    t = b.create_node_id(tag_name)
    print(t)

    t = b.create_instrument_tag(t)
    print(t)

    t = b.create_stream_id(tag_name)
    print(t)

    t = b.create_tag(pi_attribute)
    print(t)
