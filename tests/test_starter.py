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

        mock_import.return_value = mock_module
        mock_module.MbtcpServer = mock_server_class
        mock_server_class.return_value = mock_server_instance
        mock_thread.return_value = mock_thread_instance

        starter = Starter(protocol="mbtcp", port=5020, delay=1)
        starter.start_server()

        mock_import.assert_called_once_with("cursus.mbtcp.server")
        mock_server_class.assert_called_once_with(ip="127.0.0.1", port=5020)
        mock_thread.assert_called_once()

        # Check thread creation parameters
        call_kwargs = mock_thread.call_args[1]
        assert call_kwargs["target"] == mock_server_instance.start
        assert call_kwargs["name"] == "MbtcpServer"
        assert call_kwargs["daemon"] is True

        mock_thread_instance.start.assert_called_once()
        mock_sleep.assert_called_once_with(1)
        assert starter._server == mock_server_instance
        assert starter._server_thread == mock_thread_instance

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

        mock_import.return_value = mock_module
        mock_module.S7commServer = mock_server_class
        mock_server_class.return_value = mock_server_instance
        mock_thread.return_value = mock_thread_instance

        starter = Starter(protocol="s7comm", port=5102, delay=2)
        starter.start_server()

        mock_import.assert_called_once_with("cursus.s7comm.server")
        mock_server_class.assert_called_once_with(ip="127.0.0.1", port=5102)
        mock_thread.assert_called_once()

        # Check thread creation parameters
        call_kwargs = mock_thread.call_args[1]
        assert call_kwargs["target"] == mock_server_instance.start
        assert call_kwargs["name"] == "S7commServer"
        assert call_kwargs["daemon"] is True

        mock_thread_instance.start.assert_called_once()
        mock_sleep.assert_called_once_with(2)
        assert starter._server == mock_server_instance
        assert starter._server_thread == mock_thread_instance

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

        mock_import.return_value = mock_module
        mock_module.Dnp3Server = mock_server_class
        mock_server_class.return_value = mock_server_instance
        mock_thread.return_value = mock_thread_instance

        starter = Starter(protocol="dnp3", port=20000, delay=2)
        starter.start_server()

        mock_import.assert_called_once_with("cursus.dnp3.server")
        mock_server_class.assert_called_once_with(ip="127.0.0.1", port=20000)
        call_kwargs = mock_thread.call_args[1]
        assert call_kwargs["target"] == mock_server_instance.start
        assert call_kwargs["name"] == "Dnp3Server"
        assert call_kwargs["daemon"] is True
        mock_thread_instance.start.assert_called_once()
        mock_sleep.assert_called_once_with(2)
        assert starter._server == mock_server_instance
        assert starter._server_thread == mock_thread_instance

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

        mock_import.return_value = mock_module
        mock_module.MbtcpServer = mock_server_class
        mock_server_class.return_value = mock_server_instance
        mock_thread.return_value = mock_thread_instance

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

    def test_stop_server_warns_when_stop_not_supported(self) -> None:
        """Test stopping a server without a stop() implementation."""
        starter = Starter(protocol="mbtcp", port=5020, delay=1)
        starter._server = object()

        with patch.object(starter.logger, "warning") as mock_warning:
            starter.stop_server()

        mock_warning.assert_called_once_with("mbtcp server does not support stop()")

    def test_start_server_rejects_unknown_protocol(self) -> None:
        """Test that unsupported protocols fail when the module does not exist."""
        starter = Starter(protocol="opcua", port=4840, delay=1)

        with pytest.raises(ModuleNotFoundError):
            starter.start_server()
