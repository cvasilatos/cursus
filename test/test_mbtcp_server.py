"""Tests for the Modbus TCP server."""

from unittest.mock import MagicMock, Mock, patch

from cursusd.mbtcp.server import MbtcpServer


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
        assert server._identity.ProductName == "ETHERNET Programmable Fieldbus Controller"
        assert server._identity.ModelName == "PFC200"
        assert server._identity.MajorMinorRevision == "03.01.02"

    @patch("cursusd.mbtcp.server.ModbusSequentialDataBlock")
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
            assert args[0] == 0  # Starting address
            assert len(args[1]) == custom_size  # Size of data block

    @patch("cursusd.mbtcp.server.StartTcpServer")
    def test_start_server(self, mock_start_tcp: Mock) -> None:
        """Test that the server starts with correct parameters."""
        server = MbtcpServer(ip="127.0.0.1", port=5020)
        server.start()

        # Verify StartTcpServer was called once
        mock_start_tcp.assert_called_once()

        # Check the call parameters
        call_kwargs = mock_start_tcp.call_args[1]
        assert call_kwargs["context"] == server._context
        assert call_kwargs["identity"] == server._identity
        assert call_kwargs["address"] == ("127.0.0.1", 5020)

    @patch("cursusd.mbtcp.server.StartTcpServer")
    def test_start_server_with_different_address(self, mock_start_tcp: Mock) -> None:
        """Test that the server starts with different IP and port."""
        server = MbtcpServer(ip="192.168.1.50", port=5021)
        server.start()

        mock_start_tcp.assert_called_once()
        call_kwargs = mock_start_tcp.call_args[1]
        assert call_kwargs["address"] == ("192.168.1.50", 5021)

    def test_context_is_single_device(self) -> None:
        """Test that the server context is configured as single device."""
        server = MbtcpServer(ip="127.0.0.1", port=5020)

        # The context should be configured as single device
        assert server._context is not None
        # Since single=True, there should be only one device context
        assert hasattr(server._context, "single")

    @patch("cursusd.mbtcp.server.ModbusDeviceContext")
    @patch("cursusd.mbtcp.server.ModbusServerContext")
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
