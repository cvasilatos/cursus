"""Tests for the S7comm server."""

import contextlib
import ctypes
import importlib
from unittest.mock import MagicMock, Mock, patch

import snap7
from cursus.s7comm.server import S7commServer


class TestS7commServer:
    """Test suite for the S7commServer class."""

    @patch("cursus.s7comm.server.snap7.Server")
    def test_initialization_default_size(self, mock_server_class: Mock) -> None:
        """Test that S7commServer initializes with default size."""
        mock_server_instance = MagicMock()
        mock_server_class.return_value = mock_server_instance

        server = S7commServer(ip="127.0.0.1", port=5102)

        assert server._ip == "127.0.0.1"
        assert server._port == 5102
        assert server._size == 1024
        assert server._server == mock_server_instance

    @patch("cursus.s7comm.server.snap7.Server")
    def test_initialization_custom_size(self, mock_server_class: Mock) -> None:
        """Test that S7commServer initializes with custom size."""
        mock_server_instance = MagicMock()
        mock_server_class.return_value = mock_server_instance

        custom_size = 16000
        server = S7commServer(ip="192.168.1.100", port=5103, size=custom_size)

        assert server._ip == "192.168.1.100"
        assert server._port == 5103
        assert server._size == custom_size

    @patch("cursus.s7comm.server.snap7.Server")
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
        assert actual_calls[0][0][1] == 0
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

    @patch("cursus.s7comm.server.snap7.Server")
    def test_data_area_sizes(self, mock_server_class: Mock) -> None:
        """Test that data areas are initialized with correct size."""
        mock_server_instance = MagicMock()
        mock_server_class.return_value = mock_server_instance

        custom_size = 64
        _server = S7commServer(ip="127.0.0.1", port=5102, size=custom_size)

        # Check that each registered area has the correct size
        for call_args in mock_server_instance.register_area.call_args_list:
            args, _kwargs = call_args
            bytearray_data = args[2]
            assert len(bytearray_data) == custom_size
            assert isinstance(bytearray_data, ctypes.Array)

    @patch("cursus.s7comm.server.snap7.Server")
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
        mock_server_instance.start_to.assert_called_once_with("127.0.0.1", 5102)
        # Verify pick_event was called at least once
        mock_server_instance.pick_event.assert_called()
        assert server._stopped.is_set() is False

    @patch("cursus.s7comm.server.snap7.Server")
    def test_start_server_different_address(self, mock_server_class: Mock) -> None:
        """Test that the server starts with different IP and port."""
        mock_server_instance = MagicMock()
        mock_server_class.return_value = mock_server_instance
        mock_server_instance.pick_event.side_effect = KeyboardInterrupt

        server = S7commServer(ip="192.168.1.50", port=5103)

        with contextlib.suppress(KeyboardInterrupt):
            server.start()

        mock_server_instance.start_to.assert_called_once_with("192.168.1.50", 5103)

    @patch("cursus.s7comm.server.snap7.Server")
    def test_stop_server(self, mock_server_class: Mock) -> None:
        """Test that stopping the server breaks the loop and closes the listener."""
        mock_server_instance = MagicMock()
        mock_server_class.return_value = mock_server_instance

        server = S7commServer(ip="127.0.0.1", port=5102)

        server.stop()

        assert server._stopped.is_set() is True
        mock_server_instance.stop.assert_called_once_with()

    @patch("cursus.s7comm.server.snap7.Server")
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

    @patch("cursus.s7comm.server.snap7.Server")
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


def test_s7comm_server_registers_ctypes_arrays(monkeypatch):
    """Ensure the S7commServer registers ctypes arrays (not Python bytearray).

    This prevents the snap7 `sizeof()` TypeError when a Python `bytearray` is
    passed to the C API (which expects a ctypes array).
    """
    mod = importlib.import_module("cursus.s7comm.server")

    registered = []

    class FakeServer:
        def __init__(self):
            pass

        def register_area(self, area, index, userdata):
            # Should not be a Python bytearray
            assert not isinstance(userdata, bytearray), "userdata is bytearray"
            # Should be a ctypes Array instance
            assert isinstance(userdata, ctypes.Array), (
                f"userdata is not ctypes.Array: {type(userdata)}"
            )
            registered.append((area, index))
            return 0

        def start_to(self, ip, port):
            return 0

        def set_param(self, *args, **kwargs):
            return 0

        def pick_event(self):
            return 0

    # Patch snap7.Server used by the module to our FakeServer
    monkeypatch.setattr(mod.snap7, "Server", FakeServer)

    # Instantiate the server; constructor should call register_area
    srv = mod.S7commServer(ip="127.0.0.1", port=10200, size=64)

    assert registered, "register_area was not called"


def test_connect_reconnect():
    """Start a real S7commServer and verify repeated connect/disconnect cycles.

    Each client connection sends random bytes, attempts to read a response,
    then closes. This better emulates real-world traffic that can trigger
    server-side failures.
    """
    import socket
    import threading

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        host, port = probe.getsockname()

    srv = S7commServer(ip=host, port=port, size=64)
    server_errors = []

    def run_server():
        try:
            srv.start()
        except KeyboardInterrupt:
            return
        except Exception as exc:  # pragma: no cover - background failure path
            server_errors.append(exc)

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()

    def send_random_payload_and_read(ip_addr, tcp_port):
        client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_sock.settimeout(0.1)
        client_sock.connect((ip_addr, tcp_port))
        for _ in range(100):
            try:
                client_sock.sendall(
                    "0300002402f080320100000350000e0005056e140a10020001a20981a6338c00040008b7".encode()
                )
                client_sock.recv(1024)
            except socket.timeout, ConnectionResetError, BrokenPipeError:
                client_sock.close()
                client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_sock.settimeout(0.1)
                client_sock.connect((ip_addr, tcp_port))
                continue

    send_random_payload_and_read(host, port)

    assert not server_errors
    assert thread.is_alive()
