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
from pathlib import Path

# third-party
import pandas as pd

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

# Pipes are needed between "@" and "T" for child attributes
# TODO: Have not run into child attributes yet, but this well need to be added.

TAG_TO_ATTRIBUTE_HEADERS = [
    "Prefix",
    "Tags",
    "Attributes",
    "Config String",
]

# TODO: get defaults and add them as comments
KEPWARE_TO_PI_HEADERS = [
    "Selected(x)",
    "Name",
    "ObjectType",  # Pi Point
    "pointsource",
    "sourcetag",
    "pointtype",
    "engunits",
    "digitalset",
    "displaydigets",
    "Description",
    "exdesc",
    "future",
    "ptclassname",
    "archiving",
    "compressing",
    "compdev",
    "compmax",
    "compmmin",
    "compdevpercent",
    "excdev",
    "excmax",
    "excmin",
    "excdevpercent",
    "scan",
    "shutdown",
    "span",
    "step",
    "typicalvalue" "zero",
    "covers",
    "filtercode",
    "instrumenttag",
    "location1",  # 1
    "location2",  # 0
    "location3",  # 1
    "location4",  # 1
    "location5",  # 0
    "squareroot",  # 0
    "scriptid",  # 0
    "totalcode",  # 0
    "userint1",  # 0
    "userint2",  # 0
    "userreal1",  # 0
    "userreal2",  # 0
]

PI_DATA_CONVERSION_MAP = [
    # Kepware Data Type: Pi Data Type
    {"Default": "String"},
    {"String": "String"},
    {"Char": "String"},
    {"Date": "String"},
    {"Boolean": "Digital"},
    {"Float": "Float32"},
    {"Short": "Int16"},
    {"Long": "Int32"},
]

LOOKUP_KEYS = [
    "Equipment Unit Code",
    "Kepware Channel",
    "Kepware Device",
    "Department Code",
    "PI Tag Prefix Length",
    "NodeId Prefix",
    "NamespaceIndex",
]

KEPWARE_EXPORT_HEADERS = [
    "Tag Name",
    "Address",
    "Data Type",
    "Respect Data Type",
    "Client Access",
    "Scan Rate",
    "Scaling",
    "Raw Low",
    "Raw High",
    "Scaled Low",
    "Scaled High",
    "Scaled Data Type",
    "Clamp Low",
    "Clamp High",
    "Eng Units",
    "Description",
    "Negate Value",
]


class Process:
    def __init__(
        self,
        report: Reporting,
        req: TagDocGenRequest,
    ) -> None:
        self.report = report
        # Key Data
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
        self.processor_type = req.processor_type
        # Init dataframes
        self.attribute_df = pd.DataFrame(columns=TAG_TO_ATTRIBUTE_HEADERS)
        self.ua_to_filter_df = pd.DataFrame(columns=UA_FILTER_HEADERS)
        self.filter_file_df = pd.DataFrame(columns=FILTER_FILE_HEADERS)
        self.instrument_tag_df = pd.DataFrame(columns=["Instrument Tag"])
        # Input File Paths
        self.input_path = Path(req.input_path.get())

    # ---------------- #
    # DF Manipulations #
    # ---------------- #

    def create_filter_file(self, kepware_export: list[dict]):
        """
        Creates the filter file CSV from the Kepware export tag file.
        """
        self.report.simple_title("Creating Filter File")
        new_data = []
        self.report.info("All kepware records now processing...")
        for item in kepware_export:
            new_row = {}
            for header in FILTER_FILE_HEADERS:
                if header == "NodeId":
                    new_row[header] = self.create_node_id(item["Tag Name"])
                elif header == "CustomStreamId":
                    new_row[header] = self.create_stream_id(item["Tag Name"])
                else:
                    new_row[header] = None
            new_data.append(new_row)
        self.report.info("All kepware records processed into the filer file.")

        self.filter_file_df = self.append_dict_to_df(self.filter_file_df, new_data)

        file_name = self.report.report_folder / f"{self.kepware_device}-Filter_File.csv"
        self.filter_file_df.to_csv(
            file_name,
            index=False,
        )
        self.report.info(f"Filter File Saved to: {file_name}")

    def create_pi_attributes(self, kepware_export: list[dict]):
        """
        Creates the tag to attribute table.
        """
        self.report.simple_title("Creating PI Attributes")
        new_data = []
        tag_prefix = self.set_tag_prefix()
        self.report.info("All kepware records now processing...")
        for item in kepware_export:
            new_row = {}
            for header in TAG_TO_ATTRIBUTE_HEADERS:
                match header:
                    case "Prefix":
                        new_row[header] = tag_prefix
                    case "Tags":
                        new_row[header] = f'{tag_prefix}{item["Tag Name"]}'
                    case "Attributes":
                        new_row[header] = item["Tag Name"]
                    case "Config String":
                        new_row[header] = self.create_config_string(item["Tag Name"])
                    case _:
                        new_row[header] = None
            new_data.append(new_row)
        self.report.info("All kepware records now processed to PI Attributes.")

        self.attribute_df = self.append_dict_to_df(self.attribute_df, new_data)

        file_name = (
            self.report.report_folder / f"{self.kepware_device}-PI_Attributes.csv"
        )
        self.attribute_df.to_csv(
            file_name,
            index=False,
        )
        self.report.info(f"PI Attributes Saved to: {file_name}")

    def create_instrument_tags(self, kepware_export: list[dict]):
        """
        Creates the tag to attribute table.
        """
        self.report.simple_title("Creating Instrument Tags")
        new_data = []
        self.report.info("All kepware records now processing...")
        for item in kepware_export:
            new_row = {}
            node_id = self.create_node_id(item["Tag Name"])
            new_row["Instrument Tag"] = self.create_instrument_tag(node_id)
            new_data.append(new_row)
        self.report.info("All kepware records processed to Instrument Tags.")

        self.instrument_tag_df = self.append_dict_to_df(
            self.instrument_tag_df, new_data
        )

        file_name = (
            self.report.report_folder / f"{self.kepware_device}-Instrument_Tags.csv"
        )
        self.instrument_tag_df.to_csv(
            file_name,
            index=False,
        )
        self.report.info(f"Instrument Tags Saved to: {file_name}")

    def append_dict_to_df(self, df: pd.DataFrame, new_data: list[dict]) -> pd.DataFrame:
        df = pd.concat(
            [df, pd.DataFrame(new_data, columns=df.columns)], ignore_index=True
        )
        return df

    # -------------- #
    # Prefix Setters #
    # -------------- #

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

    # ---------------------------------------- #
    # PI Attributes to Tags and Config Strings #
    # ---------------------------------------- #

    def create_tag(self, pi_attribute: str) -> str:
        return self.tag_prefix + pi_attribute

    def create_config_string(self, pi_attribute: str) -> str:
        return "\\\\%Server%\\%@Tag Prefix%" + pi_attribute

    # ------------------------- #
    # Kepware Tags to UA Filter #
    # ------------------------- #

    def create_node_id(self, tag_name: str) -> str:
        return self.kepware_prefix + tag_name

    def create_stream_id(self, tag_name: str) -> str:
        return self.tag_prefix + tag_name

    # -------------- #
    # Instrument Tag #
    # -------------- #

    def create_instrument_tag(self, node_id: str) -> str:
        return node_id[7:]

    # ---------- #
    # Extraction #
    # ---------- #

    def csv_to_dict(self, input_csv_path: Path) -> list[dict]:
        df = pd.read_csv(input_csv_path)
        df = df.to_dict("records")
        return df  # type: ignore

    # ---------- #
    # Processors #
    # ---------- #

    def run(self):
        self.report.title("Tag Document Generator")
        merck_datetime = datetime.now().strftime(DATETIME_FORMAT_MERCK)
        self.report.subtitle(f"Started by {USER} on {merck_datetime}")
        self.report.info("This is just a test!")
        self.report.info(self.processor_type)

        self.process_all()

        self.report.save_report()

    def process_all(self):

        self.report.title("Tag Document Generator")
        merck_datetime = datetime.now().strftime(DATETIME_FORMAT_MERCK)
        self.report.subtitle(f"Started by {USER} on {merck_datetime}")
        self.report.info("Creating all tag documents")

        try:
            kepware_export = self.csv_to_dict(self.input_path)
            self.create_filter_file(kepware_export)
            self.create_pi_attributes(kepware_export)
            self.create_instrument_tags(kepware_export)
        except Exception as e:
            self.report.exception(f"Could not make files:\n{e}")

        self.report.save_report()

    def process_filter_file(self):
        self.report.title("Tag Document Generator")
        merck_datetime = datetime.now().strftime(DATETIME_FORMAT_MERCK)
        self.report.subtitle(f"Started by {USER} on {merck_datetime}")
        self.report.info("Creating all tag documents")

        try:
            kepware_export = self.csv_to_dict(self.input_path)
            self.create_filter_file(kepware_export)
        except Exception as e:
            self.report.exception(f"Could not make files:\n{e}")

        self.report.save_report()

    def process_attributes(self):
        self.report.title("Tag Document Generator")
        merck_datetime = datetime.now().strftime(DATETIME_FORMAT_MERCK)
        self.report.subtitle(f"Started by {USER} on {merck_datetime}")
        self.report.info("Creating all tag documents")

        try:
            kepware_export = self.csv_to_dict(self.input_path)
            self.create_pi_attributes(kepware_export)
        except Exception as e:
            self.report.exception(f"Could not make files:\n{e}")

        self.report.save_report()

    def process_instrument_tags(self):
        self.report.title("Tag Document Generator")
        merck_datetime = datetime.now().strftime(DATETIME_FORMAT_MERCK)
        self.report.subtitle(f"Started by {USER} on {merck_datetime}")
        self.report.info("Creating all tag documents")

        try:
            kepware_export = self.csv_to_dict(self.input_path)
            self.create_instrument_tags(kepware_export)
        except Exception as e:
            self.report.exception(f"Could not make files:\n{e}")

        self.report.save_report()
