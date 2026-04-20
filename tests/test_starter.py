"""Tests for the Starter class."""

from unittest.mock import MagicMock, Mock, patch

import pytest
from cursus.starter import Starter


class TestStarter:
    """Test suite for the Starter class."""

    def test_initialization(self) -> None:
        """Test that Starter initializes with correct attributes."""
        starter = Starter(protocol="mbtcp", port=5020, delay=1)

        assert starter._protocol == "mbtcp"
        assert starter._port == 5020
        assert starter._delay == 1
        assert starter._server is None
        assert starter._server_thread is None
        assert starter.ready_event.is_set() is False

    def test_initialization_different_protocol(self) -> None:
        """Test that Starter initializes with s7comm protocol."""
        starter = Starter(protocol="s7comm", port=5102, delay=2)

        assert starter._protocol == "s7comm"
        assert starter._port == 5102
        assert starter._delay == 2

    @patch("cursus.starter.importlib.import_module")
    @patch("cursus.starter.time.sleep")
    @patch("cursus.starter.threading.Thread")
    def test_start_server_mbtcp(
        self,
        mock_thread: Mock,
        mock_sleep: Mock,
        mock_import: Mock,
    ) -> None:
        """Test starting a Modbus TCP server."""
        mock_module = MagicMock()
        mock_server_class = MagicMock()
        mock_server_instance = MagicMock()
        mock_thread_instance = MagicMock()
        mock_ready_thread = MagicMock()

        mock_import.return_value = mock_module
        mock_module.MbtcpServer = mock_server_class
        mock_server_class.return_value = mock_server_instance
        mock_thread.side_effect = [mock_thread_instance, mock_ready_thread]

        starter = Starter(protocol="mbtcp", port=5020, delay=1)
        starter.start_server()

        mock_import.assert_called_once_with("cursus.mbtcp.server")
        mock_server_class.assert_called_once_with(ip="127.0.0.1", port=5020)
        assert mock_thread.call_count == 2

        # Check thread creation parameters
        call_kwargs = mock_thread.call_args_list[0][1]
        assert call_kwargs["target"] == starter._run_server
        assert call_kwargs["name"] == "MbtcpServer"
        assert call_kwargs["daemon"] is True
        ready_call_kwargs = mock_thread.call_args_list[1][1]
        assert ready_call_kwargs["target"] == starter._monitor_server_readiness
        assert ready_call_kwargs["name"] == "MbtcpServerReadyMonitor"
        assert ready_call_kwargs["daemon"] is True

        mock_thread_instance.start.assert_called_once()
        mock_ready_thread.start.assert_called_once()
        mock_sleep.assert_called_once_with(1)
        assert starter._server == mock_server_instance
        assert starter._server_thread == mock_thread_instance
        assert starter._ready_monitor_thread == mock_ready_thread

    @patch("cursus.starter.importlib.import_module")
    @patch("cursus.starter.time.sleep")
    @patch("cursus.starter.threading.Thread")
    def test_start_server_s7comm(
        self,
        mock_thread: Mock,
        mock_sleep: Mock,
        mock_import: Mock,
    ) -> None:
        """Test starting an S7comm server."""
        mock_module = MagicMock()
        mock_server_class = MagicMock()
        mock_server_instance = MagicMock()
        mock_thread_instance = MagicMock()
        mock_ready_thread = MagicMock()

        mock_import.return_value = mock_module
        mock_module.S7commServer = mock_server_class
        mock_server_class.return_value = mock_server_instance
        mock_thread.side_effect = [mock_thread_instance, mock_ready_thread]

        starter = Starter(protocol="s7comm", port=5102, delay=2)
        starter.start_server()

        mock_import.assert_called_once_with("cursus.s7comm.server")
        mock_server_class.assert_called_once_with(ip="127.0.0.1", port=5102)
        assert mock_thread.call_count == 2

        # Check thread creation parameters
        call_kwargs = mock_thread.call_args_list[0][1]
        assert call_kwargs["target"] == starter._run_server
        assert call_kwargs["name"] == "S7commServer"
        assert call_kwargs["daemon"] is True
        ready_call_kwargs = mock_thread.call_args_list[1][1]
        assert ready_call_kwargs["target"] == starter._monitor_server_readiness
        assert ready_call_kwargs["name"] == "S7commServerReadyMonitor"
        assert ready_call_kwargs["daemon"] is True

        mock_thread_instance.start.assert_called_once()
        mock_ready_thread.start.assert_called_once()
        mock_sleep.assert_called_once_with(2)
        assert starter._server == mock_server_instance
        assert starter._server_thread == mock_thread_instance
        assert starter._ready_monitor_thread == mock_ready_thread

    @patch("cursus.starter.importlib.import_module")
    @patch("cursus.starter.time.sleep")
    @patch("cursus.starter.threading.Thread")
    def test_start_server_dnp3(
        self,
        mock_thread: Mock,
        mock_sleep: Mock,
        mock_import: Mock,
    ) -> None:
        """Test starting a DNP3 server."""
        mock_module = MagicMock()
        mock_server_class = MagicMock()
        mock_server_instance = MagicMock()
        mock_thread_instance = MagicMock()
        mock_ready_thread = MagicMock()

        mock_import.return_value = mock_module
        mock_module.Dnp3Server = mock_server_class
        mock_server_class.return_value = mock_server_instance
        mock_thread.side_effect = [mock_thread_instance, mock_ready_thread]

        starter = Starter(protocol="dnp3", port=20000, delay=2)
        starter.start_server()

        mock_import.assert_called_once_with("cursus.dnp3.server")
        mock_server_class.assert_called_once_with(ip="127.0.0.1", port=20000)
        assert mock_thread.call_count == 2
        call_kwargs = mock_thread.call_args_list[0][1]
        assert call_kwargs["target"] == starter._run_server
        assert call_kwargs["name"] == "Dnp3Server"
        assert call_kwargs["daemon"] is True
        ready_call_kwargs = mock_thread.call_args_list[1][1]
        assert ready_call_kwargs["target"] == starter._monitor_server_readiness
        assert ready_call_kwargs["name"] == "Dnp3ServerReadyMonitor"
        assert ready_call_kwargs["daemon"] is True
        mock_thread_instance.start.assert_called_once()
        mock_ready_thread.start.assert_called_once()
        mock_sleep.assert_called_once_with(2)
        assert starter._server == mock_server_instance
        assert starter._server_thread == mock_thread_instance
        assert starter._ready_monitor_thread == mock_ready_thread

    @pytest.mark.parametrize("delay_value", [1, 2, 5])
    @patch("cursus.starter.importlib.import_module")
    @patch("cursus.starter.time.sleep")
    @patch("cursus.starter.threading.Thread")
    def test_start_server_with_various_delays(
        self,
        mock_thread: Mock,
        mock_sleep: Mock,
        mock_import: Mock,
        delay_value: int,
    ) -> None:
        """Test that various delay values are properly applied."""
        mock_module = MagicMock()
        mock_server_class = MagicMock()
        mock_server_instance = MagicMock()
        mock_thread_instance = MagicMock()
        mock_ready_thread = MagicMock()

        mock_import.return_value = mock_module
        mock_module.MbtcpServer = mock_server_class
        mock_server_class.return_value = mock_server_instance
        mock_thread.side_effect = [mock_thread_instance, mock_ready_thread]

        starter = Starter(protocol="mbtcp", port=5020, delay=delay_value)
        starter.start_server()

        mock_sleep.assert_called_once_with(delay_value)

    def test_stop_server_calls_backing_stop(self) -> None:
        """Test stopping a server when the backing implementation supports it."""
        starter = Starter(protocol="dnp3", port=20000, delay=2)
        mock_server = Mock()
        mock_thread = Mock()
        mock_thread.is_alive.return_value = True
        starter._server = mock_server
        starter._server_thread = mock_thread

        starter.stop_server()

        mock_server.stop.assert_called_once_with()
        mock_thread.join.assert_called_once_with(timeout=3)
        assert starter.ready_event.is_set() is False

    def test_stop_server_warns_when_stop_not_supported(self) -> None:
        """Test stopping a server without a stop() implementation."""
        starter = Starter(protocol="testproto", port=5020, delay=1)
        starter._server = object()

        with patch.object(starter.logger, "warning") as mock_warning:
            starter.stop_server()

        mock_warning.assert_called_once_with("testproto server does not support stop()")

    def test_start_server_rejects_unknown_protocol(self) -> None:
        """Test that unsupported protocols fail when the module does not exist."""
        starter = Starter(protocol="opcua", port=4840, delay=1)

        with pytest.raises(ModuleNotFoundError):
            starter.start_server()

    def test_wait_until_ready_returns_event_state(self) -> None:
        """Test waiting on the ready event."""
        starter = Starter(protocol="mbtcp", port=5020, delay=1)

        starter.ready_event.set()

        assert starter.wait_until_ready(timeout=0.1) is True

    def test_wait_until_ready_raises_when_server_failed(self) -> None:
        """Test waiting on the ready event when the backing server crashed."""
        starter = Starter(protocol="dnp3", port=20000, delay=1)
        starter._server_error = RuntimeError("compose failed")

        with pytest.raises(
            RuntimeError, match="dnp3 server failed before becoming ready"
        ):
            starter.wait_until_ready(timeout=0.01)

    @patch("cursus.starter.time.sleep")
    def test_monitor_server_readiness_sets_ready_event(
        self,
        mock_sleep: Mock,
    ) -> None:
        """Test that the readiness monitor emits the ready signal."""
        starter = Starter(protocol="mbtcp", port=5020, delay=1)
        starter._server_thread = Mock()
        starter._server_thread.is_alive.side_effect = [True, True]

        with patch.object(starter, "_is_server_ready", side_effect=[False, True]):
            starter._monitor_server_readiness()

        assert starter.ready_event.is_set() is True
        mock_sleep.assert_called_once_with(0.1)

    def test_run_server_captures_startup_error(self) -> None:
        """Test that startup errors are recorded for the caller."""
        starter = Starter(protocol="dnp3", port=20000, delay=1)
        starter._server = Mock()
        starter._server.start.side_effect = RuntimeError("compose failed")

        with patch.object(starter.logger, "exception") as mock_exception:
            starter._run_server()

        assert isinstance(starter._server_error, RuntimeError)
        mock_exception.assert_called_once_with("dnp3 server crashed during startup")

    @patch("cursus.starter.importlib.import_module")
    @patch("cursus.starter.time.sleep")
    @patch("cursus.starter.threading.Thread")
    def test_start_server_raises_when_server_thread_fails(
        self,
        mock_thread: Mock,
        mock_sleep: Mock,
        mock_import: Mock,
    ) -> None:
        """Test that startup failures are surfaced synchronously."""
        mock_module = MagicMock()
        mock_server_class = MagicMock()
        mock_server_instance = MagicMock()
        mock_thread_instance = MagicMock()
        mock_ready_thread = MagicMock()

        def _start_server() -> None:
            starter._server_error = RuntimeError("compose failed")

        mock_import.return_value = mock_module
        mock_module.Dnp3Server = mock_server_class
        mock_server_class.return_value = mock_server_instance
        mock_thread_instance.start.side_effect = _start_server
        mock_thread.side_effect = [mock_thread_instance, mock_ready_thread]

        starter = Starter(protocol="dnp3", port=20000, delay=2)

        with pytest.raises(
            RuntimeError, match="Failed to start dnp3 server on port 20000"
        ):
            starter.start_server()

        mock_sleep.assert_called_once_with(2)
