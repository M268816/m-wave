import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

from src.gui import ProcessType, ProcessRequest, Controller

# ─────────────────────────────────────────
# ProcessType Enum Tests
# ─────────────────────────────────────────


class TestProcessType:

    def test_none_value(self):
        assert ProcessType.NONE == 0

    def test_compare_value(self):
        assert ProcessType.COMPARE == 1

    def test_append_value(self):
        assert ProcessType.APPEND == 2

    def test_cast_from_int(self):
        assert ProcessType(1) == ProcessType.COMPARE

    def test_invalid_cast_raises(self):
        with pytest.raises(ValueError):
            ProcessType(99)


# ─────────────────────────────────────────
# ProcessRequest Dataclass Tests
# ─────────────────────────────────────────


class TestProcessRequest:

    def _make_request(self, filter_val="SomeFilter"):
        return ProcessRequest(
            process_type=ProcessType.COMPARE,
            filter=filter_val,
            data_table="Sheet1",
            mtl_file_path=Path("/fake/mtl.xlsx"),
            input_file_path=Path("/fake/input.csv"),
        )

    def test_report_name_with_filter(self):
        req = self._make_request(filter_val="MyFilter")
        assert req.report_name == "MyFilter"

    def test_report_name_without_filter(self):
        req = self._make_request(filter_val="")
        assert req.report_name == "No_Filter"

    def test_frozen_dataclass_is_immutable(self):
        req = self._make_request()
        with pytest.raises(Exception):  # FrozenInstanceError
            req.filter = "new_value"  # type: ignore

    @pytest.mark.parametrize(
        "filter_val, expected",
        [
            ("MyFilter", "MyFilter"),
            ("", "No_Filter"),
            ("ABC", "ABC"),
        ],
    )
    def test_report_name_parametrized(self, filter_val, expected):
        req = self._make_request(filter_val=filter_val)
        assert req.report_name == expected


# ─────────────────────────────────────────
# Controller Tests
# ─────────────────────────────────────────

# Shared fixture: a fake config dict
FAKE_CONFIG = {
    "use_timestamps": False,
    "use_msg_types": True,
    "theme": "litera",
}


@pytest.fixture
def mock_window():
    """A MagicMock standing in for a tkb.Window."""
    return MagicMock()


@pytest.fixture
def controller(mock_window):
    """
    A Controller instance with all external I/O mocked out.
    Patches: config file reading, Reporting class.
    """
    config_json = json.dumps(FAKE_CONFIG)

    with (
        patch("builtins.open", mock_open(read_data=config_json)),
        patch("src.gui.Reporting") as mock_reporting_cls,
    ):

        mock_reporting_cls.return_value = MagicMock()
        ctrl = Controller(mock_window)

    return ctrl


class TestControllerLoadConfig:

    def test_loads_valid_config(self, mock_window):
        config_json = json.dumps(FAKE_CONFIG)
        with (
            patch("builtins.open", mock_open(read_data=config_json)),
            patch("src.gui.Reporting"),
        ):
            ctrl = Controller(mock_window)
        assert ctrl.user_configs["theme"] == "litera"
        assert ctrl.user_configs["use_timestamps"] is False

    def test_raises_on_invalid_json(self, mock_window):
        with (
            patch("builtins.open", mock_open(read_data="not valid json")),
            patch("src.gui.Reporting"),
        ):
            with pytest.raises(json.JSONDecodeError):
                Controller(mock_window)


class TestControllerSetConfigValue:

    def test_blocks_change_while_thread_running(self, controller):
        """set_config_value should revert the value if a thread is alive."""
        mock_var = MagicMock()
        mock_var.get.return_value = True

        # Simulate a live thread
        mock_thread = MagicMock()
        mock_thread.is_alive.return_value = True
        controller.process_thread = mock_thread

        config_json = json.dumps(FAKE_CONFIG)
        with patch("builtins.open", mock_open(read_data=config_json)):
            controller.set_config_value("use_timestamps", mock_var)

        # Value should be reverted to whatever was in user_configs
        mock_var.set.assert_called_once_with(FAKE_CONFIG.get("use_timestamps", False))

    def test_writes_value_when_no_thread(self, controller):
        """set_config_value should write and reload config when idle."""
        controller.process_thread = None
        mock_var = MagicMock()
        mock_var.get.return_value = True

        config_json = json.dumps(FAKE_CONFIG)
        with patch("builtins.open", mock_open(read_data=config_json)):
            controller.set_config_value("use_timestamps", mock_var)

        # user_configs should be reloaded
        assert controller.user_configs is not None


class TestControllerStartProcess:

    def test_blocks_if_process_type_none(self, controller):
        """start_process should report error and return early for NONE type."""
        req = ProcessRequest(
            process_type=ProcessType.NONE,
            filter="",
            data_table="Sheet1",
            mtl_file_path=Path("/fake/mtl.xlsx"),
            input_file_path=Path("/fake/input.csv"),
        )
        ui = MagicMock()

        controller.start_process(req, ui)

        # Thread should NOT have been started
        assert controller.process_thread is None

    def test_blocks_if_thread_already_running(self, controller):
        """start_process should warn and return if a thread is already alive."""
        mock_thread = MagicMock()
        mock_thread.is_alive.return_value = True
        controller.process_thread = mock_thread

        req = ProcessRequest(
            process_type=ProcessType.COMPARE,
            filter="",
            data_table="Sheet1",
            mtl_file_path=Path("/fake/mtl.xlsx"),
            input_file_path=Path("/fake/input.csv"),
        )
        ui = MagicMock()
        controller.start_process(req, ui)

        # Still the same thread — no new one spawned
        assert controller.process_thread is mock_thread
