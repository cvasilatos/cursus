"""Tests for the Starter class."""

from unittest.mock import MagicMock, Mock, patch

from cursusd.starter import Starter


class TestStarter:
    """Test suite for the Starter class."""

    def test_initialization(self) -> None:
        """Test that Starter initializes with correct attributes."""
        starter = Starter(protocol="mbtcp", port=5020, delay=1)

        assert starter._protocol == "mbtcp"
        assert starter._port == 5020
        assert starter._delay == 1

    def test_initialization_different_protocol(self) -> None:
        """Test that Starter initializes with s7comm protocol."""
        starter = Starter(protocol="s7comm", port=5102, delay=2)

        assert starter._protocol == "s7comm"
        assert starter._port == 5102
        assert starter._delay == 2

    @patch("cursusd.starter.importlib.import_module")
    @patch("cursusd.starter.time.sleep")
    @patch("cursusd.starter.threading.Thread")
    def test_start_server_mbtcp(
        self,
        mock_thread: Mock,
        mock_sleep: Mock,
        mock_import: Mock,
    ) -> None:
        """Test starting a Modbus TCP server."""
        # Setup mocks
        mock_module = MagicMock()
        mock_server_class = MagicMock()
        mock_server_instance = MagicMock()
        mock_thread_instance = MagicMock()

        mock_import.return_value = mock_module
        mock_module.MbtcpServer = mock_server_class
        mock_server_class.return_value = mock_server_instance
        mock_thread.return_value = mock_thread_instance

        # Create starter and start server
        starter = Starter(protocol="mbtcp", port=5020, delay=1)
        starter.start_server()

        # Verify behavior
        mock_import.assert_called_once_with("cursusd.mbtcp.server")
        mock_server_class.assert_called_once_with(ip="localhost", port=5020)
        mock_thread.assert_called_once()

        # Check thread creation parameters
        call_kwargs = mock_thread.call_args[1]
        assert call_kwargs["target"] == mock_server_instance.start
        assert call_kwargs["name"] == "MbtcpServer"
        assert call_kwargs["daemon"] is True

        mock_thread_instance.start.assert_called_once()
        mock_sleep.assert_called_once_with(1)

    @patch("cursusd.starter.importlib.import_module")
    @patch("cursusd.starter.time.sleep")
    @patch("cursusd.starter.threading.Thread")
    def test_start_server_s7comm(
        self,
        mock_thread: Mock,
        mock_sleep: Mock,
        mock_import: Mock,
    ) -> None:
        """Test starting an S7comm server."""
        # Setup mocks
        mock_module = MagicMock()
        mock_server_class = MagicMock()
        mock_server_instance = MagicMock()
        mock_thread_instance = MagicMock()

        mock_import.return_value = mock_module
        mock_module.S7commServer = mock_server_class
        mock_server_class.return_value = mock_server_instance
        mock_thread.return_value = mock_thread_instance

        # Create starter and start server
        starter = Starter(protocol="s7comm", port=5102, delay=2)
        starter.start_server()

        # Verify behavior
        mock_import.assert_called_once_with("cursusd.s7comm.server")
        mock_server_class.assert_called_once_with(ip="localhost", port=5102)
        mock_thread.assert_called_once()

        # Check thread creation parameters
        call_kwargs = mock_thread.call_args[1]
        assert call_kwargs["target"] == mock_server_instance.start
        assert call_kwargs["name"] == "S7commServer"
        assert call_kwargs["daemon"] is True

        mock_thread_instance.start.assert_called_once()
        mock_sleep.assert_called_once_with(2)

    @patch("cursusd.starter.importlib.import_module")
    @patch("cursusd.starter.time.sleep")
    @patch("cursusd.starter.threading.Thread")
    def test_start_server_delay_is_applied(
        self,
        mock_thread: Mock,
        mock_sleep: Mock,
        mock_import: Mock,
    ) -> None:
        """Test that the delay is properly applied after starting the server."""
        # Setup mocks
        mock_module = MagicMock()
        mock_server_class = MagicMock()
        mock_server_instance = MagicMock()
        mock_thread_instance = MagicMock()

        mock_import.return_value = mock_module
        mock_module.MbtcpServer = mock_server_class
        mock_server_class.return_value = mock_server_instance
        mock_thread.return_value = mock_thread_instance

        # Test with different delay values
        for delay_value in [1, 5, 10]:
            mock_sleep.reset_mock()
            starter = Starter(protocol="mbtcp", port=5020, delay=delay_value)
            starter.start_server()
            mock_sleep.assert_called_once_with(delay_value)
