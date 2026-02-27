import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

DATETIME_FORMAT = "%Y-%m-%d_%H-%M-%S"


class Reporting:
    """
    A class that creates a report for a single process run by the app. It appends
    lines of strings to a list and writes them to a text file. Lines will also
    be added to the log file associated with the main logger.
    """

    def __init__(
        self, timestamp: str | None = None, output_dir: str | None = None
    ) -> None:
        if timestamp is None:
            timestamp = datetime.now().strftime(DATETIME_FORMAT)
        if output_dir is None:
            output_dir = "."
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        self.filename = f"{str(Path(output_dir))}/{timestamp}_process_report.txt"
        self.report_lines = []

    def _add_line(self, msg: str, msg_type: str | None = None) -> None:
        if msg_type is None:
            msg_type = "INFO"
        timestamp = datetime.now().strftime(DATETIME_FORMAT)
        line = f"{timestamp}:{msg_type}::{msg}"
        self.report_lines.append(line)

    def debug(self, msg: str) -> None:
        print(msg)
        logger.debug(msg)
        self._add_line(msg, "DEBUG")

    def error(self, msg: str) -> None:
        print(msg)
        logger.error(msg)
        self._add_line(msg, "ERROR")

    def info(self, msg: str) -> None:
        print(msg)
        logger.info(msg)
        self._add_line(msg, "INFO")

    def exception(self, msg: str) -> None:
        print(msg)
        logger.exception(msg)
        self._add_line(msg, "EXCEPTION")

    def save(self) -> None:
        try:
            with open(self.filename, "w", encoding="utf-8") as file:
                file.write("\n".join(self.report_lines))
            notice = f"Report saved to {self.filename}"
            print(notice)
            logger.info(notice)
        except Exception as e:
            error_msg = f"Error saving report:\n{e}"
            print(error_msg)
            logger.exception(error_msg)


if __name__ == "__main__":
    test = Reporting()
    test.info("Saving to default dir.")
    test.debug("Debugging")
    test.error("Error")
    test.exception("Exception!")
    test.save()

    test_2 = Reporting(output_dir="test_reporting")
    test_2.info("Saving to test_reporting dir.")
    test_2.debug("Debugging")
    test_2.error("Error")
    test_2.exception("Exception!")
    test_2.save()
