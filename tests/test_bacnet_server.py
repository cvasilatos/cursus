"""Tests for the BACnet/IP server."""

import socket
import struct
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager

from cursus.bacnet.server import (
    BacnetAnalogValue,
    BacnetDevice,
    BacnetServer,
    BacnetServerConfig,
)

_BVLC_ORIGINAL_UNICAST_NPDU = 0x0A
_PDU_TYPE_COMPLEX_ACK = 0x30
_PDU_TYPE_SIMPLE_ACK = 0x20
_SERVICE_READ_PROPERTY = 0x0C
_SERVICE_WRITE_PROPERTY = 0x0F
_OBJECT_TYPE_ANALOG_VALUE = 2
_OBJECT_TYPE_DEVICE = 8
_PROPERTY_OBJECT_NAME = 77
_PROPERTY_PRESENT_VALUE = 85


def _encode_context_object_identifier(
    tag_number: int, object_type: int, instance: int
) -> bytes:
    return bytes([(tag_number << 4) | 0x0C]) + struct.pack(
        ">I", (object_type << 22) | instance
    )


def _encode_context_unsigned(tag_number: int, value: int) -> bytes:
    if value == 0:
        encoded_value = b"\x00"
    else:
        encoded_value = value.to_bytes(
            max(1, (value.bit_length() + 7) // 8), byteorder="big"
        )
    if len(encoded_value) <= 4:
        return bytes([(tag_number << 4) | 0x08 | len(encoded_value)]) + encoded_value
    return bytes([(tag_number << 4) | 0x0D, len(encoded_value)]) + encoded_value


def _encode_application_real(value: float) -> bytes:
    return bytes([0x44]) + struct.pack(">f", value)


def _build_bvlc(npdu: bytes) -> bytes:
    return (
        bytes([0x81, _BVLC_ORIGINAL_UNICAST_NPDU])
        + struct.pack(">H", len(npdu) + 4)
        + npdu
    )


def _build_who_is_request() -> bytes:
    return _build_bvlc(bytes([0x01, 0x00, 0x10, 0x08]))


def _build_read_property_request(
    *, invoke_id: int, object_type: int, instance: int, property_identifier: int
) -> bytes:
    service_request = _encode_context_object_identifier(
        0, object_type, instance
    ) + _encode_context_unsigned(1, property_identifier)
    npdu = (
        bytes([0x01, 0x00, 0x00, 0x05, invoke_id, _SERVICE_READ_PROPERTY])
        + service_request
    )
    return _build_bvlc(npdu)


def _build_write_property_request(
    *, invoke_id: int, instance: int, value: float
) -> bytes:
    service_request = (
        _encode_context_object_identifier(0, _OBJECT_TYPE_ANALOG_VALUE, instance)
        + _encode_context_unsigned(1, _PROPERTY_PRESENT_VALUE)
        + bytes([0x3E])
        + _encode_application_real(value)
        + bytes([0x3F])
    )
    npdu = (
        bytes([0x01, 0x00, 0x00, 0x05, invoke_id, _SERVICE_WRITE_PROPERTY])
        + service_request
    )
    return _build_bvlc(npdu)


def _decode_application_character_string(value: bytes) -> str:
    assert value[0] == 0x75
    length = value[1]
    data = value[2 : 2 + length]
    assert data[0] == 0x00
    return data[1:].decode("ascii")


def _decode_application_real(value: bytes) -> float:
    assert value[0] == 0x44
    return struct.unpack(">f", value[1:5])[0]


def _extract_property_value(apdu: bytes) -> bytes:
    offset = 3
    assert apdu[offset] == 0x0C
    offset += 5
    assert (apdu[offset] >> 4) == 1
    property_tag = apdu[offset]
    property_length = (
        property_tag & 0x07 if (property_tag & 0x07) != 5 else apdu[offset + 1]
    )
    offset += 1 if (property_tag & 0x07) != 5 else 2
    offset += property_length
    assert apdu[offset] == 0x3E
    offset += 1
    return apdu[offset:-1]


@contextmanager
def _running_server(
    config: BacnetServerConfig | None = None,
) -> Iterator[tuple[BacnetServer, str, int]]:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        probe.bind(("127.0.0.1", 0))
        host, port = probe.getsockname()

    server = BacnetServer(ip=host, port=port, config=config)
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
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client:
                client.settimeout(0.1)
                client.sendto(_build_who_is_request(), (host, port))
                response, _address = client.recvfrom(1024)
                if response[6:8] == bytes([0x10, 0x00]):
                    break
        except OSError:
            time.sleep(0.05)
    else:  # pragma: no cover - environment timing failure
        raise AssertionError("BACnet/IP server did not become reachable")

    try:
        yield server, host, port
    finally:
        server.stop()
        thread.join(timeout=2)
        assert background_errors == []


class TestBacnetServer:
    """Test suite for the BacnetServer class."""

    def test_initialization_default_config(self) -> None:
        """Test that the server initializes with default device and object values."""
        server = BacnetServer(ip="127.0.0.1", port=47808)

        assert server._ip == "127.0.0.1"
        assert server._port == 47808
        assert server._config.device.instance == 1234
        assert server.get_present_value(1) == 0.0

    def test_who_is_returns_i_am(self) -> None:
        """Test that a Who-Is request returns an I-Am response."""
        config = BacnetServerConfig(
            device=BacnetDevice(instance=4321, vendor_identifier=321)
        )

        with _running_server(config=config) as (_server, host, port):
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client:
                client.settimeout(1)
                client.sendto(_build_who_is_request(), (host, port))
                response, _address = client.recvfrom(1024)

        assert response[:2] == bytes([0x81, _BVLC_ORIGINAL_UNICAST_NPDU])
        assert response[4:6] == bytes([0x01, 0x00])
        assert response[6:8] == bytes([0x10, 0x00])
        assert response[8] == 0xC4
        device_identifier = struct.unpack(">I", response[9:13])[0]
        assert device_identifier == (_OBJECT_TYPE_DEVICE << 22) | 4321

    def test_read_property_returns_device_object_name(self) -> None:
        """Test reading the device object-name property."""
        config = BacnetServerConfig(
            device=BacnetDevice(instance=2222, object_name="Boiler-1")
        )

        with _running_server(config=config) as (_server, host, port):
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client:
                client.settimeout(1)
                client.sendto(
                    _build_read_property_request(
                        invoke_id=7,
                        object_type=_OBJECT_TYPE_DEVICE,
                        instance=2222,
                        property_identifier=_PROPERTY_OBJECT_NAME,
                    ),
                    (host, port),
                )
                response, _address = client.recvfrom(1024)

        apdu = response[6:]
        assert apdu[:3] == bytes([_PDU_TYPE_COMPLEX_ACK, 7, _SERVICE_READ_PROPERTY])
        assert (
            _decode_application_character_string(_extract_property_value(apdu))
            == "Boiler-1"
        )

    def test_write_property_updates_present_value(self) -> None:
        """Test writing and then reading an analog-value present-value."""
        config = BacnetServerConfig(
            analog_values={
                3: BacnetAnalogValue(
                    instance=3, object_name="TankLevel", present_value=1.0
                ),
            }
        )

        with _running_server(config=config) as (server, host, port):
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client:
                client.settimeout(1)
                client.sendto(
                    _build_write_property_request(invoke_id=11, instance=3, value=12.5),
                    (host, port),
                )
                response, _address = client.recvfrom(1024)

                assert response[6:9] == bytes(
                    [_PDU_TYPE_SIMPLE_ACK, 11, _SERVICE_WRITE_PROPERTY]
                )
                assert server.get_present_value(3) == 12.5

                client.sendto(
                    _build_read_property_request(
                        invoke_id=12,
                        object_type=_OBJECT_TYPE_ANALOG_VALUE,
                        instance=3,
                        property_identifier=_PROPERTY_PRESENT_VALUE,
                    ),
                    (host, port),
                )
                response, _address = client.recvfrom(1024)

        apdu = response[6:]
        assert apdu[:3] == bytes([_PDU_TYPE_COMPLEX_ACK, 12, _SERVICE_READ_PROPERTY])
        assert _decode_application_real(_extract_property_value(apdu)) == 12.5
