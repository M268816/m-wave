# Copyright 2026 Merck KGaA, Darmstadt, Germany and/or its affiliates.
# All rights reserved
#
# Author: Raymond Comeau, MilliporeSigma Data Systems Technician, Jaffrey NH

# stdio
from dataclasses import dataclass
from enum import Enum

# third-party
import ttkbootstrap as tkb
from ttkbootstrap.widgets.scrolled import ScrolledText

# local


class DocGeneratorType(str, Enum):
    NONE = "Select a Generator"
    ALL = "All Documents"
    KEPWARE_TAG_TO_ATTRIBUTE = "Kepware Tags to PI Attributes"
    KEPWARE_TO_FILTER = "Kepware Tags to Filter File"
    KEPWARE_TO_PI_TAGS = "Kepware Tags to PI Tags (20701076)"
    INSTRUMENT_TAGS = "Kepware Tags to Instrument Tags"
    PI_TAGS_TO_KEPWARE_TAGS = "Pi Tags to Kepware Tags"


class TagFileType(str, Enum):
    NONE = "Select a file type"
    KEPWARE_TAGS = "Kepware Tags"
    PI_TAGS = "PI Tags (Doc# 20701076)"


TAG_GEN_FILE_OPTIONS: dict[TagFileType, list[DocGeneratorType]] = {
    TagFileType.NONE: [
        DocGeneratorType.NONE,
    ],
    TagFileType.KEPWARE_TAGS: [
        DocGeneratorType.NONE,
        DocGeneratorType.ALL,
        DocGeneratorType.KEPWARE_TAG_TO_ATTRIBUTE,
        DocGeneratorType.KEPWARE_TO_FILTER,
        DocGeneratorType.INSTRUMENT_TAGS,
        DocGeneratorType.KEPWARE_TO_PI_TAGS,
    ],
    TagFileType.PI_TAGS: [
        DocGeneratorType.NONE,
        DocGeneratorType.ALL,
        DocGeneratorType.PI_TAGS_TO_KEPWARE_TAGS,
    ],
}


@dataclass
class ProcessRequest:
    """
    Data class that captures a processes data for manipulation.
    """

    report_name: str
    input_path: tkb.StringVar
    equipment_code: tkb.StringVar
    kepware_channel: tkb.StringVar
    kepware_device: tkb.StringVar
    department_code: tkb.StringVar
    tag_prefix_length: tkb.StringVar
    node_id_prefix: tkb.StringVar
    namespace_index: tkb.StringVar
    processor_type: DocGeneratorType
    file_type: TagFileType


@dataclass
class UiContext:
    """
    Data class that captures a processes UI widgets for manipulation.
    """

    equipment_code: tkb.Entry
    kepware_channel: tkb.Entry
    kepware_device: tkb.Entry
    department_code: tkb.Entry
    tag_prefix_length: tkb.Spinbox
    node_id_prefix: tkb.Entry
    namespace_index: tkb.Spinbox
    progress_bar: tkb.Progressbar
    gen_opt_cbox: tkb.Combobox
    scrolled_text: ScrolledText
    process_button: tkb.Button
