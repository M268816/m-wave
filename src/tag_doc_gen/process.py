# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
#
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH


# stdio
from datetime import datetime
from pathlib import Path
from typing import Callable

# third-party
import pandas as pd

# local
from src.app.reporting import Reporting
from src.app.utils import DATETIME_FORMAT_MERCK, USER
from src.tag_doc_gen.utils import TagDocGenRequest, TagGeneratorType, TagGenFileType

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

TAG_TO_ATTRIBUTE_HEADERS = [
    "Prefix",
    "Tags",
    "Attributes",
    "Config String",
]

KEPWARE_TO_PI_HEADERS = [
    "Selected(x)",
    "Name",
    "ObjectType",
    "pointsource",
    "sourcetag",
    "pointtype",
    "engunits",
    "digitalset",
    "displaydigits",
    "Description",
    "exdesc",
    "future",
    "ptclassname",
    "archiving",
    "compressing",
    "compdev",
    "compmax",
    "compmin",
    "compdevpercent",
    "excdev",
    "excmax",
    "excmin",
    "excdevpercent",
    "scan",
    "shutdown",
    "span",
    "step",
    "typicalvalue",
    "zero",
    "convers",
    "filtercode",
    "instrumenttag",
    "location1",
    "location2",
    "location3",
    "location4",
    "location5",
    "squareroot",
    "scriptid",
    "totalcode",
    "userint1",
    "userint2",
    "userreal1",
    "userreal2",
]

KEPWARE_TO_PI_DEFAULTS = {
    "Selected(x)": "x",
    "ObjectType": "PIPoint",
    "pointsource": "<I.T. INPUT FIELD>",  # IT fills in
    "digitalset": "<USER INPUT FIELD>",  # Digital set name, or blank
    "sourcetag": "<I.T. INPUT FIELD>",  # IT fills in
    "engunits": "<USER INPUT FIELD>",  # Engineering units (blank if unitless)
    "displaydigits": "<USER INPUT FIELD>",  # -20 to 10 (int)
    "exdesc": None,  # Extended descriptor / free text
    "future": 0,  # Most tags; cannot change after creation
    "ptclassname": "classic",
    "archiving": 1,  # Actively archived
    "compressing": 1,  # Compression enabled
    "compdev": 0,  # Compression deviation (eng units)
    "compmax": 28800,  # Max seconds between archive events
    "compmin": 0,  # Min seconds between archive events
    "compdevpercent": 0,  # Compression deviation (% of span)
    "excdev": 0,  # Exception deviation (eng units)
    "excmax": 0,  # Max seconds between reported values
    "excmin": 0,  # Min seconds between reported values (usually 0)
    "excdevpercent": 0,  # Exception deviation (% of span)
    "scan": 1,  # Scan mode: 0-5
    "shutdown": 0,  # Active (not shut down)
    "span": "<USER INPUT FIELD>",  # Full-scale range (numeric points only)
    "step": "<USER INPUT FIELD>",  # 1=stepped, 0=interpolated
    "typicalvalue": "<USER INPUT FIELD>",  # Typical value if known
    "zero": "<USER INPUT FIELD>",  # Raw value = 0 EU
    "convers": "<USER INPUT FIELD>",  # Conversion multiplier for totalizer (usually 1)
    "filtercode": "<USER INPUT FIELD>",  # Data filter/validation code
    "location1": 1,
    "location2": 0,
    "location3": 1,
    "location4": 1,
    "location5": 0,
    "squareroot": 0,
    "scriptid": 0,
    "totalcode": 0,
    "userint1": 0,
    "userint2": 0,
    "userreal1": 0,
    "userreal2": 0,
}

KEPWARE_TO_PI_AUTO_INPUTS = [
    "Name",  # Meaningful tag name
    "pointtype",  # Digital, Float64, Float32, Int32, Int16, String
    "Description",  # 255-char max
    "instrumenttag",  # PLC / controller tag name (full path)
]

PI_DATA_CONVERSION_MAP = {
    # Lookups with Kepware values returns Pi values
    "DEFAULT": "STRING",
    "STRING": "STRING",
    "CHAR": "STRING",
    "LONG": "INT32",
    "SHORT": "INT16",
    "DOUBLE": "FLOAT64",
    "FLOAT": "FLOAT32",
    "DATE": "TIMESTAMP",
    "BOOLEAN": "DIGITAL",
}

KEPWARE_DATA_CONVERSION_MAP = {
    # Lookups with Pi values returns Kepware Values
    "STRING": "STRING",
    "INT32": "LONG",
    "INT16": "SHORT",
    "FLOAT64": "DOUBLE",
    "FLOAT32": "FLOAT",
    "TIMESTAMP": "DATE",
    "DIGITAL": "BOOLEAN",
}

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
        self.report.info(f"Filter File Saved to: ../{file_name.name}")

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
        self.report.info(f"PI Attributes Saved to: ../{file_name.name}")

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
        self.report.info(f"Instrument Tags Saved to: ../{file_name.name}")

    def append_dict_to_df(self, df: pd.DataFrame, new_data: list[dict]) -> pd.DataFrame:
        df = pd.concat(
            [df, pd.DataFrame(new_data, columns=df.columns)], ignore_index=True
        )
        return df

    def create_pi_tags(self, kepware_data: list[dict]) -> None:
        """
        Creates a data structure that holds tag data formatted for PI connectors from
        document (20701076) supplied from Kepware csv data.
        """
        pi_data = []
        for item in kepware_data:
            new_row = dict(KEPWARE_TO_PI_DEFAULTS)
            for header in KEPWARE_TO_PI_AUTO_INPUTS:
                match header:
                    case "Name":
                        new_row[header] = item["Tag Name"]
                    case "pointtype":
                        new_row[header] = self.pi_datatype_conversion(item["Data Type"])
                    case "instrumenttag":
                        new_row[header] = item["Address"]
                    case _:
                        try:
                            new_row[header] = item[header]
                        except KeyError:
                            new_row[header] = None

            original_row = new_row.copy()
            new_row = {col: original_row[col] for col in KEPWARE_TO_PI_HEADERS}

            pi_data.append(new_row)

        df = self.append_dict_to_df(
            pd.DataFrame(columns=KEPWARE_TO_PI_HEADERS), pi_data
        )
        df = df.sort_values(by="instrumenttag")

        file_name = self.report.report_folder / f"{self.kepware_device}-Pi_Tags.csv"
        df.to_csv(
            file_name,
            index=False,
        )
        self.report.info("Kepware Tags Transferred to PI Tags")
        self.report.info(f"New file saved to: ../{file_name.name}")

    def create_kepware_tags(self, pi_data: list[dict]) -> None | pd.DataFrame:
        """
        Creates a data structure that holds tag data formatted like Kepware csv
        import/export files supplied from PI tag data formatted from document (20701076).
        """
        kepware_data = []
        for item in pi_data:
            new_row = {}
            for header in KEPWARE_EXPORT_HEADERS:
                match header:
                    case "Tag Name":
                        new_row[header] = item["Name"]
                    case "Address":
                        new_row[header] = item["instrumenttag"]
                    case "Data Type":
                        new_row[header] = self.kepware_datatype_conversion(
                            item["pointtype"]
                        )
                    case "Respect Data Type":
                        new_row[header] = 1
                    case "Client Access":
                        new_row[header] = "R/W"
                    case "Scan Rate":
                        new_row[header] = 100
                    case _:
                        try:
                            new_row[header] = item[header]
                        except KeyError:
                            new_row[header] = None
            kepware_data.append(new_row)

        df = self.append_dict_to_df(
            pd.DataFrame(columns=KEPWARE_EXPORT_HEADERS), kepware_data
        )
        df = df.sort_values(by="Address")

        file_name = (
            self.report.report_folder / f"{self.kepware_device}-Kepware_Tags.csv"
        )
        df.to_csv(
            file_name,
            index=False,
        )
        self.report.info("PI Tags Transferred to Kepware Tags")
        self.report.info(f"New file saved to: ../{file_name.name}")

        return df

    def kepware_datatype_conversion(self, data_type: str) -> str:
        """
        Converts a PI Tag data type to a Kepware Tag Datatype
        """
        d_type = data_type.upper()
        return KEPWARE_DATA_CONVERSION_MAP[d_type]

    def pi_datatype_conversion(self, data_type: str) -> str:
        """
        Converts a Kepware data type to a PI tag data type.
        """
        d_type = data_type.upper()
        return PI_DATA_CONVERSION_MAP[d_type]

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

    def document_original_input(self, input_path: Path) -> None:
        df = pd.read_csv(input_path)
        file_name = self.report.report_folder / f"{self.kepware_device}-Original.csv"
        df.to_csv(
            file_name,
            index=False,
        )
        self.report.info("Original Dataset Captured and Saved to folder.")
        self.report.info(f"File saved to: ../{file_name.name}")

    # ---------- #
    # Processors #
    # ---------- #

    def run(self, gen_type: TagGeneratorType, file_type: TagGenFileType):
        self.report.title("Tag Document Generator")
        merck_datetime = datetime.now().strftime(DATETIME_FORMAT_MERCK)
        self.report.subtitle(f"Started by {USER} on {merck_datetime}")
        self.report.subtitle(
            f"Generating {gen_type.value} for {file_type.value} document."
        )

        generators: dict[TagGenFileType, dict[TagGeneratorType, Callable]] = {
            TagGenFileType.PI_TAGS: {
                TagGeneratorType.ALL: self.process_pi_all,
                TagGeneratorType.PI_TAGS_TO_KEPWARE_TAGS: self.process_pi_to_kepware,
            },
            TagGenFileType.KEPWARE_TAGS: {
                TagGeneratorType.ALL: self.process_kepware_all,
                TagGeneratorType.KEPWARE_TAG_TO_ATTRIBUTE: self.process_attributes,
                TagGeneratorType.KEPWARE_TO_FILTER: self.process_filter_file,
                TagGeneratorType.KEPWARE_TO_PI_TAGS: self.process_kepware_to_pi,
                TagGeneratorType.INSTRUMENT_TAGS: self.process_instrument_tags,
            },
        }

        self.document_original_input(self.input_path)

        if gen_type == TagGeneratorType.ALL:
            if file_type == TagGenFileType.KEPWARE_TAGS:
                self.process_kepware_all()
            else:
                self.process_pi_all()
        else:
            process = generators[file_type][gen_type]
            process()

        self.report.save_report()

    def process_pi_all(self):
        """
        Processes pi tags into kepware tags, then takes the kepware tags and makes
        all possible files from that.
        """
        try:
            pi_import = self.csv_to_dict(self.input_path)
            kepware_tags = self.create_kepware_tags(pi_import)
            kepware_dict = kepware_tags.to_dict("records")  # type: ignore
            self.create_filter_file(kepware_dict)
            self.create_pi_attributes(kepware_dict)
            self.create_instrument_tags(kepware_dict)
        except Exception as e:
            self.report.exception(f"could not make files:\n{e}")

    def process_pi_to_kepware(self) -> None | pd.DataFrame:
        """
        Process for turning pi tags into kepware tags.
        """
        try:
            pi_import = self.csv_to_dict(self.input_path)
            kepware_tags = self.create_kepware_tags(pi_import)
        except Exception as e:
            self.report.exception(f"Could not make files:\n{e}")
        return kepware_tags

    def process_kepware_all(self):
        """
        Processes all files that can be obtained from a kepware tag export file.
        """
        try:
            kepware_export = self.csv_to_dict(self.input_path)
            self.create_filter_file(kepware_export)
            self.create_pi_attributes(kepware_export)
            self.create_instrument_tags(kepware_export)
            self.create_pi_tags(kepware_export)
        except Exception as e:
            self.report.exception(f"Could not make files:\n{e}")

    def process_filter_file(self):
        """
        Processes a kepware tag export file into a PI filter file.
        """
        try:
            kepware_export = self.csv_to_dict(self.input_path)
            self.create_filter_file(kepware_export)
        except Exception as e:
            self.report.exception(f"Could not make files:\n{e}")

    def process_attributes(self):
        """
        Processes a kepware tag export file into a PI attribute helper file.
        """
        try:
            kepware_export = self.csv_to_dict(self.input_path)
            self.create_pi_attributes(kepware_export)
        except Exception as e:
            self.report.exception(f"Could not make files:\n{e}")

    def process_instrument_tags(self):
        """
        Processes a kepware tag export file into a PI instrument tag helper file.
        """
        try:
            kepware_export = self.csv_to_dict(self.input_path)
            self.create_instrument_tags(kepware_export)
        except Exception as e:
            self.report.exception(f"Could not make files:\n{e}")

    def process_kepware_to_pi(self):
        """
        Process for turning kepware tags into pi tags.
        """
        try:
            kepware_export = self.csv_to_dict(self.input_path)
            self.create_pi_tags(kepware_export)
        except Exception as e:
            self.report.exception(f"Could not make files:\n{e}")
