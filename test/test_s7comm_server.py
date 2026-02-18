"""Tests for the S7comm server."""

import contextlib
from unittest.mock import MagicMock, Mock, patch

import snap7

from cursusd.s7comm.server import S7commServer


class TestS7commServer:
    """Test suite for the S7commServer class."""

    @patch("cursusd.s7comm.server.snap7.Server")
    def test_initialization_default_size(self, mock_server_class: Mock) -> None:
        """Test that S7commServer initializes with default size."""
        mock_server_instance = MagicMock()
        mock_server_class.return_value = mock_server_instance

        server = S7commServer(ip="127.0.0.1", port=5102)

        assert server._ip == "127.0.0.1"
        assert server._port == 5102
        assert server._size == 32000
        assert server._server == mock_server_instance

    @patch("cursusd.s7comm.server.snap7.Server")
    def test_initialization_custom_size(self, mock_server_class: Mock) -> None:
        """Test that S7commServer initializes with custom size."""
        mock_server_instance = MagicMock()
        mock_server_class.return_value = mock_server_instance

        custom_size = 16000
        server = S7commServer(ip="192.168.1.100", port=5103, size=custom_size)

        assert server._ip == "192.168.1.100"
        assert server._port == 5103
        assert server._size == custom_size

    @patch("cursusd.s7comm.server.snap7.Server")
    def test_register_all_data_areas(self, mock_server_class: Mock) -> None:
        """Test that all data areas are registered correctly."""
        mock_server_instance = MagicMock()
        mock_server_class.return_value = mock_server_instance

        custom_size = 1000
        _server = S7commServer(ip="127.0.0.1", port=5102, size=custom_size)

        # Verify register_area was called 6 times (DB, PA, PE, MK, TM, CT)
        assert mock_server_instance.register_area.call_count == 6

        # Check the area types and indices
        actual_calls = mock_server_instance.register_area.call_args_list
        assert actual_calls[0][0][0] == snap7.SrvArea.DB
        assert actual_calls[0][0][1] == 1
        assert actual_calls[1][0][0] == snap7.SrvArea.PA
        assert actual_calls[1][0][1] == 0
        assert actual_calls[2][0][0] == snap7.SrvArea.PE
        assert actual_calls[2][0][1] == 0
        assert actual_calls[3][0][0] == snap7.SrvArea.MK
        assert actual_calls[3][0][1] == 0
        assert actual_calls[4][0][0] == snap7.SrvArea.TM
        assert actual_calls[4][0][1] == 0
        assert actual_calls[5][0][0] == snap7.SrvArea.CT
        assert actual_calls[5][0][1] == 0

    @patch("cursusd.s7comm.server.snap7.Server")
    def test_data_area_sizes(self, mock_server_class: Mock) -> None:
        """Test that data areas are initialized with correct size."""
        mock_server_instance = MagicMock()
        mock_server_class.return_value = mock_server_instance

        custom_size = 2000
        _server = S7commServer(ip="127.0.0.1", port=5102, size=custom_size)

        # Check that each registered area has the correct size
        for call_args in mock_server_instance.register_area.call_args_list:
            args, _kwargs = call_args
            bytearray_data = args[2]
            assert len(bytearray_data) == custom_size
            assert isinstance(bytearray_data, bytearray)

    @patch("cursusd.s7comm.server.snap7.Server")
    def test_start_server(self, mock_server_class: Mock) -> None:
        """Test that the server starts with correct parameters."""
        mock_server_instance = MagicMock()
        mock_server_class.return_value = mock_server_instance

        # Make pick_event raise an exception after the first call to break the loop
        mock_server_instance.pick_event.side_effect = KeyboardInterrupt

        server = S7commServer(ip="127.0.0.1", port=5102)

        # Start the server (will be interrupted)
        with contextlib.suppress(KeyboardInterrupt):
            server.start()

        # Verify start_to was called with correct parameters
        mock_server_instance.start_to.assert_called_once_with("127.0.0.1", tcpport=5102)
        # Verify pick_event was called at least once
        mock_server_instance.pick_event.assert_called()

    @patch("cursusd.s7comm.server.snap7.Server")
    def test_start_server_different_address(self, mock_server_class: Mock) -> None:
        """Test that the server starts with different IP and port."""
        mock_server_instance = MagicMock()
        mock_server_class.return_value = mock_server_instance
        mock_server_instance.pick_event.side_effect = KeyboardInterrupt

        server = S7commServer(ip="192.168.1.50", port=5103)

        with contextlib.suppress(KeyboardInterrupt):
            server.start()

        mock_server_instance.start_to.assert_called_once_with("192.168.1.50", tcpport=5103)

    @patch("cursusd.s7comm.server.snap7.Server")
    def test_server_event_loop(self, mock_server_class: Mock) -> None:
        """Test that the server continuously picks events."""
        mock_server_instance = MagicMock()
        mock_server_class.return_value = mock_server_instance

        # Make pick_event raise after 3 calls to verify the loop
        call_count = [0]

        def side_effect():
            call_count[0] += 1
            if call_count[0] > 3:
                raise KeyboardInterrupt

        mock_server_instance.pick_event.side_effect = side_effect

        server = S7commServer(ip="127.0.0.1", port=5102)

        with contextlib.suppress(KeyboardInterrupt):
            server.start()

        # Verify pick_event was called multiple times
        assert mock_server_instance.pick_event.call_count == 4

    @patch("cursusd.s7comm.server.snap7.Server")
    def test_bytearray_initialization(self, mock_server_class: Mock) -> None:
        """Test that bytearrays are properly initialized."""
        mock_server_instance = MagicMock()
        mock_server_class.return_value = mock_server_instance

        _server = S7commServer(ip="127.0.0.1", port=5102, size=100)

        # Verify all registered bytearrays are zero-initialized
        for call_args in mock_server_instance.register_area.call_args_list:
            args, _kwargs = call_args
            bytearray_data = args[2]
            # Check that all bytes are initially zero
            assert all(byte == 0 for byte in bytearray_data)
