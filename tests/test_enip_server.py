"""Tests for the EtherNet/IP server."""

import socket
import struct
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager

from cursus.enip.server import EnipIdentity, EnipServer, EnipServerConfig

_ENCAPSULATION_HEADER = struct.Struct("<HHII8sI")

_COMMAND_LIST_SERVICES = 0x0004
_COMMAND_LIST_IDENTITY = 0x0063
_COMMAND_REGISTER_SESSION = 0x0065
_COMMAND_SEND_RR_DATA = 0x006F

_CPF_ITEM_UNCONNECTED_DATA = 0x00B2

_CIP_SERVICE_GET_ATTRIBUTE_SINGLE = 0x0E
_CIP_SERVICE_SET_ATTRIBUTE_SINGLE = 0x10


def _build_frame(
    command: int,
    *,
    session_handle: int = 0,
    payload: bytes = b"",
    sender_context: bytes = b"cursus01",
) -> bytes:
    return (
        _ENCAPSULATION_HEADER.pack(
            command,
            len(payload),
            session_handle,
            0,
            sender_context,
            0,
        )
        + payload
    )


def _receive_frame(client: socket.socket) -> tuple[int, int, int, bytes]:
    header = b""
    while len(header) < _ENCAPSULATION_HEADER.size:
        header += client.recv(_ENCAPSULATION_HEADER.size - len(header))
    command, length, session_handle, status, _sender_context, _options = (
        _ENCAPSULATION_HEADER.unpack(header)
    )
    payload = b""
    while len(payload) < length:
        payload += client.recv(length - len(payload))
    return command, session_handle, status, payload


def _build_cip_request(service: int, path: bytes, data: bytes = b"") -> bytes:
    return bytes([service, len(path) // 2]) + path + data


def _build_send_rr_data(cip_payload: bytes) -> bytes:
    return (
        struct.pack("<IHH", 0, 0, 2)
        + struct.pack("<HH", 0, 0)
        + struct.pack("<HH", _CPF_ITEM_UNCONNECTED_DATA, len(cip_payload))
        + cip_payload
    )


def _extract_cip_response(payload: bytes) -> bytes:
    interface_handle, _timeout, item_count = struct.unpack_from("<IHH", payload, 0)
    assert interface_handle == 0
    assert item_count == 2

    offset = 8
    cip_response = b""
    for _ in range(item_count):
        item_type, item_length = struct.unpack_from("<HH", payload, offset)
        offset += 4
        item_data = payload[offset : offset + item_length]
        offset += item_length
        if item_type == _CPF_ITEM_UNCONNECTED_DATA:
            cip_response = item_data

    return cip_response


@contextmanager
def _running_server(
    config: EnipServerConfig | None = None,
) -> Iterator[tuple[EnipServer, str, int]]:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        host, port = probe.getsockname()

    server = EnipServer(ip=host, port=port, config=config)
    background_errors: list[Exception] = []

    def run_server() -> None:
        try:
            server.start()
        except Exception as exc:  # pragma: no cover - background failure path
            background_errors.append(exc)

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()

    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.1):
                break
        except OSError:
            time.sleep(0.05)
    else:  # pragma: no cover - environment timing failure
        raise AssertionError("EtherNet/IP server did not become reachable")

    try:
        yield server, host, port
    finally:
        server.stop()
        thread.join(timeout=2)
        assert background_errors == []


class TestEnipServer:
    """Test suite for the EnipServer class."""

    def test_initialization_default_config(self) -> None:
        """Test that the server initializes with Allen-Bradley-like defaults."""
        server = EnipServer(ip="127.0.0.1", port=44818)

        assert server._ip == "127.0.0.1"
        assert server._port == 44818
        assert server._config.identity.vendor_id == 1
        assert server.get_assembly_data(100) == bytes(32)

    def test_list_services_and_list_identity(self) -> None:
        """Test discovery responses over a real TCP socket."""
        identity = EnipIdentity(product_code=77, product_name="1756-L81E/B")
        config = EnipServerConfig(identity=identity)

        with _running_server(config=config) as (_server, host, port):
            with socket.create_connection((host, port), timeout=1) as client:
                client.sendall(_build_frame(_COMMAND_LIST_SERVICES))
                command, session_handle, status, payload = _receive_frame(client)

                assert command == _COMMAND_LIST_SERVICES
                assert session_handle == 0
                assert status == 0
                assert struct.unpack_from("<H", payload, 0)[0] == 1
                assert payload.endswith(b"Communications\x00\x00")

                client.sendall(_build_frame(_COMMAND_LIST_IDENTITY))
                command, session_handle, status, payload = _receive_frame(client)

                assert command == _COMMAND_LIST_IDENTITY
                assert session_handle == 0
                assert status == 0
                assert struct.unpack_from("<H", payload, 0)[0] == 1
                item_length = struct.unpack_from("<H", payload, 4)[0]
                item_data = payload[6 : 6 + item_length]
                assert struct.unpack_from("<H", item_data, 0)[0] == 1
                assert struct.unpack_from("<H", item_data, 18)[0] == identity.vendor_id
                assert (
                    struct.unpack_from("<H", item_data, 22)[0] == identity.product_code
                )
                product_name_length = item_data[32]
                product_name = item_data[33 : 33 + product_name_length].decode("ascii")
                assert product_name == "1756-L81E/B"

    def test_explicit_message_reads_identity_attribute(self) -> None:
        """Test a CIP Get_Attribute_Single request over SendRRData."""
        with _running_server() as (_server, host, port):
            with socket.create_connection((host, port), timeout=1) as client:
                register_payload = struct.pack("<HH", 1, 0)
                client.sendall(
                    _build_frame(
                        _COMMAND_REGISTER_SESSION,
                        payload=register_payload,
                    )
                )
                _command, session_handle, status, payload = _receive_frame(client)
                assert status == 0
                assert payload == register_payload

                path = bytes([0x20, 0x01, 0x24, 0x01, 0x30, 0x07])
                cip_request = _build_cip_request(
                    _CIP_SERVICE_GET_ATTRIBUTE_SINGLE, path
                )
                client.sendall(
                    _build_frame(
                        _COMMAND_SEND_RR_DATA,
                        session_handle=session_handle,
                        payload=_build_send_rr_data(cip_request),
                    )
                )
                command, response_session, response_status, payload = _receive_frame(
                    client
                )

                assert command == _COMMAND_SEND_RR_DATA
                assert response_session == session_handle
                assert response_status == 0
                cip_response = _extract_cip_response(payload)
                assert cip_response[:4] == bytes([0x8E, 0x00, 0x00, 0x00])
                name_length = cip_response[4]
                assert (
                    cip_response[5 : 5 + name_length].decode("ascii") == "1756-EN2T/A"
                )

    def test_explicit_message_writes_assembly_data(self) -> None:
        """Test CIP Set_Attribute_Single and Get_Attribute_Single for Assembly data."""
        with _running_server() as (server, host, port):
            with socket.create_connection((host, port), timeout=1) as client:
                register_payload = struct.pack("<HH", 1, 0)
                client.sendall(
                    _build_frame(
                        _COMMAND_REGISTER_SESSION,
                        payload=register_payload,
                    )
                )
                _command, session_handle, _status, _payload = _receive_frame(client)

                path = bytes([0x20, 0x04, 0x24, 0x64, 0x30, 0x03])
                set_request = _build_cip_request(
                    _CIP_SERVICE_SET_ATTRIBUTE_SINGLE,
                    path,
                    b"\x11\x22\x33\x44",
                )
                client.sendall(
                    _build_frame(
                        _COMMAND_SEND_RR_DATA,
                        session_handle=session_handle,
                        payload=_build_send_rr_data(set_request),
                    )
                )
                _command, _session, response_status, payload = _receive_frame(client)
                assert response_status == 0
                assert _extract_cip_response(payload) == bytes([0x90, 0x00, 0x00, 0x00])
                assert server.get_assembly_data(100) == b"\x11\x22\x33\x44"

                get_request = _build_cip_request(
                    _CIP_SERVICE_GET_ATTRIBUTE_SINGLE, path
                )
                client.sendall(
                    _build_frame(
                        _COMMAND_SEND_RR_DATA,
                        session_handle=session_handle,
                        payload=_build_send_rr_data(get_request),
                    )
                )
                _command, _session, response_status, payload = _receive_frame(client)
                assert response_status == 0
                assert _extract_cip_response(payload)[4:] == b"\x11\x22\x33\x44"

    def test_send_rr_data_rejects_unknown_session(self) -> None:
        """Test that SendRRData rejects requests with an invalid session handle."""
        with _running_server() as (_server, host, port):
            with socket.create_connection((host, port), timeout=1) as client:
                path = bytes([0x20, 0x01, 0x24, 0x01, 0x30, 0x01])
                cip_request = _build_cip_request(
                    _CIP_SERVICE_GET_ATTRIBUTE_SINGLE, path
                )
                client.sendall(
                    _build_frame(
                        _COMMAND_SEND_RR_DATA,
                        session_handle=999,
                        payload=_build_send_rr_data(cip_request),
                    )
                )
                command, session_handle, status, _payload = _receive_frame(client)

                assert command == _COMMAND_SEND_RR_DATA
                assert session_handle == 999
                assert status == 0x0064
