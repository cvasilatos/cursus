"""Tests for the Modbus TCP server."""

import asyncio
from unittest.mock import MagicMock, Mock, patch

from cursus.mbtcp.server import MbtcpServer


class TestMbtcpServer:
    """Test suite for the MbtcpServer class."""

    def test_initialization_default_size(self) -> None:
        """Test that MbtcpServer initializes with default size."""
        server = MbtcpServer(ip="127.0.0.1", port=5020)

        assert server._ip == "127.0.0.1"
        assert server._port == 5020
        assert server._context is not None
        assert server._identity is not None

    def test_initialization_custom_size(self) -> None:
        """Test that MbtcpServer initializes with custom size."""
        custom_size = 16000
        server = MbtcpServer(ip="192.168.1.100", port=5021, size=custom_size)

        assert server._ip == "192.168.1.100"
        assert server._port == 5021
        assert server._context is not None
        assert server._identity is not None

    def test_device_identity_configuration(self) -> None:
        """Test that device identity is properly configured."""
        server = MbtcpServer(ip="127.0.0.1", port=5020)

        assert server._identity.VendorName == "WAGO"
        assert server._identity.ProductCode == "750-881"
        assert server._identity.VendorUrl == "https://www.wago.com"
        assert (
            server._identity.ProductName == "ETHERNET Programmable Fieldbus Controller"
        )
        assert server._identity.ModelName == "PFC200"
        assert server._identity.MajorMinorRevision == "03.01.02"

    @patch("cursus.mbtcp.server.ModbusSequentialDataBlock")
    def test_data_blocks_initialized(self, mock_data_block: Mock) -> None:
        """Test that all data blocks are initialized with correct size."""
        custom_size = 16000
        mock_block_instance = MagicMock()
        mock_data_block.return_value = mock_block_instance

        _server = MbtcpServer(ip="127.0.0.1", port=5020, size=custom_size)

        # Verify ModbusSequentialDataBlock was called 4 times (ir, hr, di, co)
        assert mock_data_block.call_count == 4

        # Verify each call had correct parameters
        for call_args in mock_data_block.call_args_list:
            args, _kwargs = call_args
            assert args[0] == 1  # Starting address
            assert len(args[1]) == custom_size  # Size of data block

    @patch("cursus.mbtcp.server.ModbusTcpServer")
    def test_start_server(self, mock_server_class: Mock) -> None:
        """Test that the server starts with correct parameters."""
        mock_server = MagicMock()
        mock_server.serve_forever = MagicMock(side_effect=lambda: asyncio.sleep(0))
        mock_server_class.return_value = mock_server
        server = MbtcpServer(ip="127.0.0.1", port=5020)
        server.start()

        mock_server_class.assert_called_once()
        call_kwargs = mock_server_class.call_args[1]
        assert call_kwargs["context"] == server._context
        assert call_kwargs["identity"] == server._identity
        assert call_kwargs["address"] == ("127.0.0.1", 5020)
        mock_server.serve_forever.assert_called_once_with()
        assert server._server is None
        assert server._loop is None

    @patch("cursus.mbtcp.server.ModbusTcpServer")
    def test_start_server_with_different_address(self, mock_server_class: Mock) -> None:
        """Test that the server starts with different IP and port."""
        mock_server = MagicMock()
        mock_server.serve_forever = MagicMock(side_effect=lambda: asyncio.sleep(0))
        mock_server_class.return_value = mock_server
        server = MbtcpServer(ip="192.168.1.50", port=5021)
        server.start()

        mock_server_class.assert_called_once()
        call_kwargs = mock_server_class.call_args[1]
        assert call_kwargs["address"] == ("192.168.1.50", 5021)
        mock_server.serve_forever.assert_called_once_with()

    @patch("cursus.mbtcp.server.asyncio.run_coroutine_threadsafe")
    def test_stop_server(self, mock_run_coroutine_threadsafe: Mock) -> None:
        """Test that the server shuts down the active Modbus listener."""
        server = MbtcpServer(ip="127.0.0.1", port=5020)
        mock_server = MagicMock()
        mock_loop = MagicMock()
        mock_future = MagicMock()
        mock_run_coroutine_threadsafe.return_value = mock_future
        server._server = mock_server
        server._loop = mock_loop

        server.stop()

        mock_server.shutdown.assert_called_once_with()
        mock_run_coroutine_threadsafe.assert_called_once_with(
            mock_server.shutdown.return_value,
            mock_loop,
        )
        mock_future.result.assert_called_once_with(timeout=5)

    def test_context_is_single_device(self) -> None:
        """Test that the server context is configured as single device."""
        server = MbtcpServer(ip="127.0.0.1", port=5020)

        # The context should be configured as single device
        assert server._context is not None
        # Since single=True, there should be only one device context
        assert hasattr(server._context, "single")

    @patch("cursus.mbtcp.server.ModbusDeviceContext")
    @patch("cursus.mbtcp.server.ModbusServerContext")
    def test_server_context_creation(
        self,
        mock_server_context: Mock,
        mock_device_context: Mock,
    ) -> None:
        """Test that server context is created correctly."""
        mock_device_instance = MagicMock()
        mock_server_instance = MagicMock()
        mock_device_context.return_value = mock_device_instance
        mock_server_context.return_value = mock_server_instance

        _server = MbtcpServer(ip="127.0.0.1", port=5020)

        # Verify ModbusDeviceContext was called with correct parameters
        mock_device_context.assert_called_once()
        call_kwargs = mock_device_context.call_args[1]
        assert "ir" in call_kwargs
        assert "hr" in call_kwargs
        assert "di" in call_kwargs
        assert "co" in call_kwargs

        # Verify ModbusServerContext was called with device store and single=True
        mock_server_context.assert_called_once()
        server_call_kwargs = mock_server_context.call_args[1]
        assert server_call_kwargs["devices"] == mock_device_instance
        assert server_call_kwargs["single"] is True
