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

# local core
from m_wave.core.reporting import Reporting
from m_wave.core.utils import DATETIME_FORMAT_MERCK, USER

# local wave pack
from m_wave.wave_packs.tag_doc_gen.metadata import Metadata
from m_wave.wave_packs.tag_doc_gen.utils import (
    ProcessRequest,
    DocGeneratorType,
    TagFileType,
)


class Process:
    def __init__(
        self,
        report: Reporting,
        req: ProcessRequest,
    ) -> None:
        self.report = report
        self.metadata: Metadata = Metadata(self.report)
        self.req = req
        # Key Data
        self.site = "USJA"
        self.tag_prefix = self.set_tag_prefix()
        self.kepware_prefix = self.set_kepware_prefix()
        # Init dataframes
        self.attribute_df = pd.DataFrame(
            columns=self.metadata.get_tag_to_attribute_headers()
        )
        self.ua_to_filter_df = pd.DataFrame(
            columns=self.metadata.get_ua_filter_headers()
        )
        self.filter_file_df = pd.DataFrame(
            columns=self.metadata.get_filter_file_headers()
        )
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
        self.report.simple_title("Creating a Filter File")

        new_data = []
        for item in kepware_export:
            self.report.info(f'Processing:\t{item["Tag Name"]}')
            new_row = {}
            for header in self.metadata.get_filter_file_headers():
                if header == "NodeId":
                    new_row[header] = self.create_node_id(item["Tag Name"])
                elif header == "CustomStreamId":
                    new_row[header] = self.create_stream_id(item["Tag Name"])
                else:
                    new_row[header] = None
            new_data.append(new_row)
        self.report.info("All records processed into the filer file.")

        self.filter_file_df = self.append_dict_to_df(self.filter_file_df, new_data)

        file_name = self.report.report_folder / (
            f"{self.req.kepware_device.get()}" + "-Filter_File.csv"
        )
        self.filter_file_df.to_csv(
            file_name,
            index=False,
        )
        self.report.info(f"Filter File Saved to: ..//{file_name.name}")

    def create_pi_attributes(self, kepware_export: list[dict]):
        """
        Creates the tag to attribute table.
        """
        self.report.simple_title("Creating PI Attributes")
        new_data = []
        tag_prefix = self.set_tag_prefix()
        for item in kepware_export:
            new_row = {}
            self.report.info(f'Processing:\t{item["Tag Name"]}')
            for header in self.metadata.get_tag_to_attribute_headers():
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
        self.report.info("All records processed to PI Attributes.")

        self.attribute_df = self.append_dict_to_df(self.attribute_df, new_data)

        file_name = self.report.report_folder / (
            f"{self.req.kepware_device.get()}-PI_Attributes.csv"
        )
        self.attribute_df.to_csv(
            file_name,
            index=False,
        )
        self.report.info(f"PI Attributes Saved to: ..//{file_name.name}")

    def create_instrument_tags(self, kepware_export: list[dict]):
        """
        Creates the tag to attribute table.
        """
        self.report.simple_title("Creating Instrument Tags")
        new_data = []
        for item in kepware_export:
            self.report.info(f'Processing:\t{item["Tag Name"]}')
            new_row = {}
            node_id = self.create_node_id(item["Tag Name"])
            new_row["Instrument Tag"] = self.create_instrument_tag(node_id)
            new_data.append(new_row)
        self.report.info("All kepware records processed to Instrument Tags.")

        self.instrument_tag_df = self.append_dict_to_df(
            self.instrument_tag_df, new_data
        )

        file_name = self.report.report_folder / (
            f"{self.req.kepware_device.get()}-Instrument_Tags.csv"
        )
        self.instrument_tag_df.to_csv(
            file_name,
            index=False,
        )
        self.report.info(f"Instrument Tags Saved to: ..//{file_name.name}")

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
        self.report.simple_title("Creating PI Tags (20701076)")
        pi_data = []
        for item in kepware_data:
            self.report.info(f'Processing:\t{item["Tag Name"]}')
            new_row = dict(self.metadata.get_kepware_to_pi_defaults())
            for header in self.metadata.get_kepware_to_pi_auto_inputs():
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
                            self.report.error(
                                f"KeyError: PI tag header: {header} does not exist."
                            )
                            new_row[header] = None

            original_row = new_row.copy()
            new_row = {
                col: original_row[col]
                for col in self.metadata.get_kepware_to_pi_headers()
            }

            pi_data.append(new_row)

        df = self.append_dict_to_df(
            pd.DataFrame(columns=self.metadata.get_kepware_to_pi_headers()), pi_data
        )
        df = df.sort_values(by="instrumenttag")

        file_name = (
            self.report.report_folder / f"{self.req.kepware_device.get()}-Pi_Tags.csv"
        )
        df.to_csv(
            file_name,
            index=False,
        )
        self.report.info("Kepware Tags Transferred to PI Tags")
        self.report.info(f"New file saved to: ..//{file_name.name}")

    def create_kepware_tags(self, pi_data: list[dict]) -> None | pd.DataFrame:
        """
        Creates a data structure that holds tag data formatted like Kepware csv
        import/export files supplied from PI tag data formatted from document (20701076).
        """
        kepware_data = []
        for item in pi_data:
            self.report.info(f'Processing:\t{item["Name"]}')
            new_row = {}
            for header in self.metadata.get_kepware_export_headers():
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
            pd.DataFrame(columns=self.metadata.get_kepware_export_headers()),
            kepware_data,
        )
        df = df.sort_values(by="Address")

        file_name = (
            self.report.report_folder
            / f"{self.req.kepware_device.get()}-Kepware_Tags.csv"
        )
        df.to_csv(
            file_name,
            index=False,
        )
        self.report.info("PI Tags Transferred to Kepware Tags")
        self.report.info(f"New file saved to: ..//{file_name.name}")

        return df

    def kepware_datatype_conversion(self, data_type: str) -> str:
        """
        Converts a PI Tag data type to a Kepware Tag Datatype
        """
        d_type = data_type.upper()
        return self.metadata.get_kepware_data_conversion_map()[d_type]

    def pi_datatype_conversion(self, data_type: str) -> str:
        """
        Converts a Kepware data type to a PI tag data type.
        """
        d_type = data_type.upper()
        return self.metadata.get_pi_data_conversion_map()[d_type]

    # -------------- #
    # Prefix Setters #
    # -------------- #

    def set_tag_prefix(self) -> str:
        lst: list[str] = []
        lst.append(self.site)
        lst.append(self.req.department_code.get())
        lst.append(self.req.equipment_code.get())
        return "_".join(lst) + "_"

    def set_kepware_prefix(self) -> str:
        return (
            self.req.node_id_prefix.get()
            + self.req.kepware_channel.get()
            + "."
            + self.req.kepware_device.get()
            + "."
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
        file_name = self.report.report_folder / (
            f"{self.req.kepware_device.get()}-Original.csv"
        )
        df.to_csv(
            file_name,
            index=False,
        )
        self.report.info("Original dataset captured.")
        self.report.info(f"File saved as: ..//{file_name.name}")

    # ---------- #
    # Processors #
    # ---------- #

    def run(self, gen_type: DocGeneratorType, file_type: TagFileType):
        self.report.title("Tag Document Generator")
        merck_datetime = datetime.now().strftime(DATETIME_FORMAT_MERCK)
        self.report.subtitle(f"Started by {USER} on {merck_datetime}")
        self.report.subtitle(
            f"Generating {gen_type.value} for {file_type.value} document."
        )

        generators: dict[TagFileType, dict[DocGeneratorType, Callable]] = {
            TagFileType.PI_TAGS: {
                DocGeneratorType.ALL: self.process_pi_all,
                DocGeneratorType.PI_TAGS_TO_KEPWARE_TAGS: self.process_pi_to_kepware,
            },
            TagFileType.KEPWARE_TAGS: {
                DocGeneratorType.ALL: self.process_kepware_all,
                DocGeneratorType.KEPWARE_TAG_TO_ATTRIBUTE: self.process_attributes,
                DocGeneratorType.KEPWARE_TO_FILTER: self.process_filter_file,
                DocGeneratorType.KEPWARE_TO_PI_TAGS: self.process_kepware_to_pi,
                DocGeneratorType.INSTRUMENT_TAGS: self.process_instrument_tags,
            },
        }

        self.document_original_input(self.input_path)

        if gen_type == DocGeneratorType.ALL:
            if file_type == TagFileType.KEPWARE_TAGS:
                self.process_kepware_all()
            else:
                self.process_pi_all()
        else:
            process = generators[file_type][gen_type]
            process()

        self.report_process_complete()
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

    def report_process_complete(self):
        """
        Report process has ended.
        """
        self.report.subtitle("Process has completed")
        self.report.info("Review log files for errors.")
