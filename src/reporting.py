import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

DATETIME_FORMAT = "%Y-%m-%dT%H_%M_%S-%f"


class Reporting:
    """
    A class that creates a report for a single process run by the app. It appends
    lines of strings to a list and writes them to a text file. Lines will also
    be added to the log file associated with the main logger.
    """

    def __init__(
        self, name: str, timestamp: str | None = None, output_dir: str | None = None
    ) -> None:
        if timestamp is None:
            timestamp = datetime.now().strftime(DATETIME_FORMAT)
        if output_dir is None:
            output_dir = "."
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        self.name = name
        self.dir_path = f"{str(Path(output_dir))}/"
        self.report_name = f"{timestamp}_{name.replace(' ', '_')}"
        self.file_name = f"{self.dir_path}{self.report_name}"
        self.full_path = f"{self.file_name}.log"
        self.report_lines = []

    def _add_line(self, msg: str, msg_type: str | None = None) -> None:
        if msg_type is None:
            msg_type = "INFO"
        timestamp = datetime.now().strftime(DATETIME_FORMAT)
        line = f"{timestamp}:{msg_type}::{msg}"
        self.report_lines.append(line)

    def debug(self, msg: str, log_only: bool = False) -> None:
        print(msg)
        logger.debug(msg)
        if log_only:
            return None
        self._add_line(msg, "DEBUG")

    def error(self, msg: str, log_only: bool = False) -> None:
        print(msg)
        logger.error(msg)
        if log_only:
            return None
        self._add_line(msg, "ERROR")

    def exception(self, msg: str, log_only: bool = False) -> None:
        print(msg)
        logger.exception(msg)
        if log_only:
            return None
        self._add_line(msg, "EXCEPTION")

    def info(self, msg: str, log_only: bool = False) -> None:
        print(msg)
        logger.info(msg)
        if log_only:
            return None
        self._add_line(msg, "INFO")

    def warning(self, msg: str, log_only: bool = False) -> None:
        print(msg)
        logger.warning(msg)
        if log_only:
            return None
        self._add_line(msg, "WARNING")

    def save(self) -> None:
        try:
            notice = f"{self.name} report saved to: {self.full_path}"
            self._add_line(notice, "INFO")
            with open(self.full_path, "w", encoding="utf-8") as file:
                file.write("\n".join(self.report_lines))
            print(notice)
            logger.info(notice)
        except Exception as e:
            error_msg = f"Error saving report:\n{e}"
            print(error_msg)
            logger.exception(error_msg)


if __name__ == "__main__":
    test = Reporting("reporting_test", output_dir="test_reporting")
    test.info("Saving to test_reporting dir.")
    test.info("Only shown in logging, not reporting", True)
    test.debug("Debugging")
    test.error("Error")
    test.exception("Exception!")
    test.save()
