import logging
import socketserver
import struct
import threading
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    import socket

    from decima.logger import CustomLogger


_BVLC_TYPE_BACNET_IP = 0x81
_BVLC_ORIGINAL_UNICAST_NPDU = 0x0A
_BVLC_ORIGINAL_BROADCAST_NPDU = 0x0B

_NPDU_VERSION = 0x01
_NPDU_CONTROL_NO_EXPECTING_REPLY = 0x00

_PDU_TYPE_CONFIRMED_REQUEST = 0x00
_PDU_TYPE_UNCONFIRMED_REQUEST = 0x10
_PDU_TYPE_SIMPLE_ACK = 0x20
_PDU_TYPE_COMPLEX_ACK = 0x30

_SERVICE_WHO_IS = 0x08
_SERVICE_I_AM = 0x00
_SERVICE_READ_PROPERTY = 0x0C
_SERVICE_WRITE_PROPERTY = 0x0F

_OBJECT_TYPE_ANALOG_VALUE = 2
_OBJECT_TYPE_DEVICE = 8

_PROPERTY_DESCRIPTION = 28
_PROPERTY_MODEL_NAME = 70
_PROPERTY_OBJECT_IDENTIFIER = 75
_PROPERTY_OBJECT_LIST = 76
_PROPERTY_OBJECT_NAME = 77
_PROPERTY_OBJECT_TYPE = 79
_PROPERTY_PRESENT_VALUE = 85
_PROPERTY_PROTOCOL_VERSION = 98
_PROPERTY_PROTOCOL_REVISION = 99
_PROPERTY_SEGMENTATION_SUPPORTED = 107
_PROPERTY_STATUS_FLAGS = 111
_PROPERTY_UNITS = 117
_PROPERTY_VENDOR_IDENTIFIER = 120
_PROPERTY_VENDOR_NAME = 121
_PROPERTY_MAX_APDU_LENGTH_ACCEPTED = 62

_SEGMENTATION_NO_SEGMENTATION = 3
_UNITS_NO_UNITS = 95

_APPLICATION_TAG_UNSIGNED = 2
_APPLICATION_TAG_REAL = 4
_APPLICATION_TAG_CHARACTER_STRING = 7
_APPLICATION_TAG_BIT_STRING = 8
_APPLICATION_TAG_ENUMERATED = 9
_APPLICATION_TAG_OBJECT_IDENTIFIER = 12

_CONTEXT_TAG_OBJECT_IDENTIFIER = 0
_CONTEXT_TAG_PROPERTY_IDENTIFIER = 1
_CONTEXT_TAG_PROPERTY_ARRAY_INDEX = 2
_CONTEXT_TAG_PROPERTY_VALUE = 3

_BACNET_IP_DEFAULT_PORT = 47808
_BVLC_HEADER_SIZE = 4
_NPDU_HEADER_SIZE = 2
_CONFIRMED_REQUEST_HEADER_SIZE = 4
_APPLICATION_REAL_LENGTH = 4
_APPLICATION_REAL_TOTAL_SIZE = 5
_CONTEXT_CLASS_BIT = 0x08
_EXTENDED_LENGTH_SENTINEL = 5
_MAX_INLINE_LENGTH = 4


@dataclass(slots=True)
class BacnetDevice:
    """BACnet device object values returned by the emulator."""

    instance: int = 1234
    object_name: str = "Cursus BACnet Device"
    description: str = "BACnet/IP emulator"
    vendor_name: str = "Cursus"
    vendor_identifier: int = 999
    model_name: str = "Cursus BACnet/IP"
    max_apdu_length_accepted: int = 1476
    segmentation_supported: int = _SEGMENTATION_NO_SEGMENTATION
    protocol_version: int = 1
    protocol_revision: int = 14


@dataclass(slots=True)
class BacnetAnalogValue:
    """BACnet analog-value object exposed by the emulator."""

    instance: int
    object_name: str
    description: str = ""
    present_value: float = 0.0
    units: int = _UNITS_NO_UNITS


@dataclass(slots=True)
class BacnetServerConfig:
    """Configuration for the BACnet/IP server."""

    device: BacnetDevice = field(default_factory=BacnetDevice)
    analog_values: dict[int, BacnetAnalogValue] = field(
        default_factory=lambda: {
            1: BacnetAnalogValue(instance=1, object_name="AV-1", description="Analog Value 1", present_value=0.0),
            2: BacnetAnalogValue(instance=2, object_name="AV-2", description="Analog Value 2", present_value=0.0),
        }
    )


@dataclass(slots=True)
class _BacnetUdpPacket:
    payload: bytes
    client_address: tuple[str, int]


class _BacnetUdpServer(socketserver.ThreadingUDPServer):
    allow_reuse_address = True
    daemon_threads = True
    block_on_close = False
    protocol: "BacnetServer"


class _BacnetRequestHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        server = cast("_BacnetUdpServer", self.server)
        protocol = server.protocol
        request = cast("tuple[bytes, socket.socket]", self.request)
        data, transport = request
        response = protocol.handle_datagram(
            packet=_BacnetUdpPacket(payload=data, client_address=self.client_address),
        )
        if response is not None:
            transport.sendto(response, self.client_address)


class BacnetServer:
    """BACnet/IP server implementation for basic device discovery and property access."""

    def __init__(
        self,
        ip: str,
        port: int = _BACNET_IP_DEFAULT_PORT,
        config: BacnetServerConfig | None = None,
    ) -> None:
        """Initialize the BACnet/IP emulator."""
        logger_name = f"{self.__class__.__module__}.{self.__class__.__name__}"
        self.logger: CustomLogger = cast("CustomLogger", logging.getLogger(logger_name))
        self._ip = ip
        self._port = port
        self._config = config or BacnetServerConfig()
        self._server: _BacnetUdpServer | None = None
        self._analog_value_lock = threading.Lock()
        self._analog_values = {
            instance: BacnetAnalogValue(
                instance=value.instance,
                object_name=value.object_name,
                description=value.description,
                present_value=value.present_value,
                units=value.units,
            )
            for instance, value in self._config.analog_values.items()
        }

    def start(self) -> None:
        """Start the BACnet/IP UDP server and block until stopped."""
        self.logger.info(f"Starting BACnet/IP server at {self._ip}:{self._port}")
        server = _BacnetUdpServer((self._ip, self._port), _BacnetRequestHandler)
        server.protocol = self
        self._server = server

        try:
            server.serve_forever()
        finally:
            server.server_close()
            self._server = None

    def stop(self) -> None:
        """Stop the BACnet/IP server when it is running."""
        if self._server is None:
            return

        self.logger.info(f"Stopping BACnet/IP server at {self._ip}:{self._port}")
        self._server.shutdown()

    def get_present_value(self, instance: int) -> float:
        """Return the present value for an analog-value object."""
        with self._analog_value_lock:
            return self._analog_values[instance].present_value

    def set_present_value(self, instance: int, value: float) -> None:
        """Set the present value for an analog-value object."""
        with self._analog_value_lock:
            self._analog_values[instance].present_value = value

    def handle_datagram(self, *, packet: _BacnetUdpPacket) -> bytes | None:
        """Handle a single BACnet/IP datagram."""
        payload = packet.payload
        if len(payload) < _BVLC_HEADER_SIZE or payload[0] != _BVLC_TYPE_BACNET_IP:
            return None

        bvlc_function = payload[1]
        if bvlc_function not in {
            _BVLC_ORIGINAL_UNICAST_NPDU,
            _BVLC_ORIGINAL_BROADCAST_NPDU,
        }:
            return None

        bvlc_length = struct.unpack(">H", payload[2:4])[0]
        if bvlc_length != len(payload):
            return None

        response_npdu = self._handle_npdu(payload[_BVLC_HEADER_SIZE:])
        if response_npdu is None:
            return None

        return self._build_bvlc(
            function=_BVLC_ORIGINAL_UNICAST_NPDU,
            npdu=response_npdu,
        )

    def _handle_npdu(self, npdu: bytes) -> bytes | None:
        if len(npdu) < _NPDU_HEADER_SIZE or npdu[0] != _NPDU_VERSION:
            return None

        control = npdu[1]
        offset = 2
        if control & 0x20:
            if len(npdu) < offset + 3:
                return None
            destination_length = npdu[offset + 2]
            offset += 3 + destination_length + 1
        if control & 0x08:
            if len(npdu) < offset + 3:
                return None
            source_length = npdu[offset + 2]
            offset += 3 + source_length
        if control & 0x80:
            offset += 1
        if len(npdu) < offset:
            return None

        apdu = npdu[offset:]
        response_apdu = self._handle_apdu(apdu)
        if response_apdu is None:
            return None

        return bytes([_NPDU_VERSION, _NPDU_CONTROL_NO_EXPECTING_REPLY]) + response_apdu

    def _handle_apdu(self, apdu: bytes) -> bytes | None:
        if len(apdu) < _NPDU_HEADER_SIZE:
            return None

        pdu_type = apdu[0] & 0xF0
        if pdu_type == _PDU_TYPE_UNCONFIRMED_REQUEST:
            return self._handle_unconfirmed_request(apdu)
        if pdu_type == _PDU_TYPE_CONFIRMED_REQUEST:
            return self._handle_confirmed_request(apdu)

        return None

    def _handle_unconfirmed_request(self, apdu: bytes) -> bytes | None:
        service_choice = apdu[1]
        if service_choice != _SERVICE_WHO_IS:
            return None

        lower_limit, upper_limit = self._parse_who_is_limits(apdu[2:])
        device_instance = self._config.device.instance
        if lower_limit is not None and device_instance < lower_limit:
            return None
        if upper_limit is not None and device_instance > upper_limit:
            return None

        return self._build_i_am_apdu()

    def _handle_confirmed_request(self, apdu: bytes) -> bytes | None:
        if len(apdu) < _CONFIRMED_REQUEST_HEADER_SIZE:
            return None

        invoke_id = apdu[2]
        service_choice = apdu[3]
        service_request = apdu[4:]

        if service_choice == _SERVICE_READ_PROPERTY:
            return self._handle_read_property(invoke_id=invoke_id, payload=service_request)
        if service_choice == _SERVICE_WRITE_PROPERTY:
            return self._handle_write_property(invoke_id=invoke_id, payload=service_request)

        return None

    def _handle_read_property(self, *, invoke_id: int, payload: bytes) -> bytes | None:
        parsed = self._parse_property_reference(payload)
        if parsed is None:
            return None

        object_type, instance, property_identifier = parsed
        property_value = self._read_property(
            object_type=object_type,
            instance=instance,
            property_identifier=property_identifier,
        )
        if property_value is None:
            return None

        ack_payload = (
            self._encode_context_object_identifier(_CONTEXT_TAG_OBJECT_IDENTIFIER, object_type, instance)
            + self._encode_context_unsigned(_CONTEXT_TAG_PROPERTY_IDENTIFIER, property_identifier)
            + self._encode_opening_tag(_CONTEXT_TAG_PROPERTY_VALUE)
            + property_value
            + self._encode_closing_tag(_CONTEXT_TAG_PROPERTY_VALUE)
        )
        return bytes([_PDU_TYPE_COMPLEX_ACK, invoke_id, _SERVICE_READ_PROPERTY]) + ack_payload

    def _handle_write_property(self, *, invoke_id: int, payload: bytes) -> bytes | None:
        parsed = self._parse_write_property_request(payload)
        if parsed is None:
            return None

        object_type, instance, property_identifier, property_value = parsed
        if not self._write_property(
            object_type=object_type,
            instance=instance,
            property_identifier=property_identifier,
            property_value=property_value,
        ):
            return None

        return bytes([_PDU_TYPE_SIMPLE_ACK, invoke_id, _SERVICE_WRITE_PROPERTY])

    def _read_property(self, *, object_type: int, instance: int, property_identifier: int) -> bytes | None:
        if object_type == _OBJECT_TYPE_DEVICE and instance == self._config.device.instance:
            return self._read_device_property(property_identifier)
        if object_type == _OBJECT_TYPE_ANALOG_VALUE:
            return self._read_analog_value_property(instance, property_identifier)

        return None

    def _read_device_property(self, property_identifier: int) -> bytes | None:
        device = self._config.device
        properties = {
            _PROPERTY_OBJECT_IDENTIFIER: self._encode_application_object_identifier(_OBJECT_TYPE_DEVICE, device.instance),
            _PROPERTY_OBJECT_NAME: self._encode_application_character_string(device.object_name),
            _PROPERTY_OBJECT_TYPE: self._encode_application_enumerated(_OBJECT_TYPE_DEVICE),
            _PROPERTY_DESCRIPTION: self._encode_application_character_string(device.description),
            _PROPERTY_VENDOR_NAME: self._encode_application_character_string(device.vendor_name),
            _PROPERTY_VENDOR_IDENTIFIER: self._encode_application_unsigned(device.vendor_identifier),
            _PROPERTY_MODEL_NAME: self._encode_application_character_string(device.model_name),
            _PROPERTY_MAX_APDU_LENGTH_ACCEPTED: self._encode_application_unsigned(device.max_apdu_length_accepted),
            _PROPERTY_SEGMENTATION_SUPPORTED: self._encode_application_enumerated(device.segmentation_supported),
            _PROPERTY_PROTOCOL_VERSION: self._encode_application_unsigned(device.protocol_version),
            _PROPERTY_PROTOCOL_REVISION: self._encode_application_unsigned(device.protocol_revision),
            _PROPERTY_OBJECT_LIST: self._encode_application_object_identifier(_OBJECT_TYPE_DEVICE, device.instance),
        }
        return properties.get(property_identifier)

    def _read_analog_value_property(self, instance: int, property_identifier: int) -> bytes | None:
        with self._analog_value_lock:
            analog_value = self._analog_values.get(instance)

        if analog_value is None:
            return None

        properties = {
            _PROPERTY_OBJECT_IDENTIFIER: self._encode_application_object_identifier(_OBJECT_TYPE_ANALOG_VALUE, analog_value.instance),
            _PROPERTY_OBJECT_NAME: self._encode_application_character_string(analog_value.object_name),
            _PROPERTY_OBJECT_TYPE: self._encode_application_enumerated(_OBJECT_TYPE_ANALOG_VALUE),
            _PROPERTY_DESCRIPTION: self._encode_application_character_string(analog_value.description),
            _PROPERTY_PRESENT_VALUE: self._encode_application_real(analog_value.present_value),
            _PROPERTY_UNITS: self._encode_application_enumerated(analog_value.units),
            _PROPERTY_STATUS_FLAGS: self._encode_application_bit_string(b"\x00"),
        }
        return properties.get(property_identifier)

    def _write_property(
        self,
        *,
        object_type: int,
        instance: int,
        property_identifier: int,
        property_value: bytes,
    ) -> bool:
        if object_type != _OBJECT_TYPE_ANALOG_VALUE or property_identifier != _PROPERTY_PRESENT_VALUE:
            return False

        decoded_value = self._decode_application_real(property_value)
        if decoded_value is None:
            return False

        with self._analog_value_lock:
            analog_value = self._analog_values.get(instance)
            if analog_value is None:
                return False
            analog_value.present_value = decoded_value

        return True

    def _build_i_am_apdu(self) -> bytes:
        device = self._config.device
        return (
            bytes([_PDU_TYPE_UNCONFIRMED_REQUEST, _SERVICE_I_AM])
            + self._encode_application_object_identifier(_OBJECT_TYPE_DEVICE, device.instance)
            + self._encode_application_unsigned(device.max_apdu_length_accepted)
            + self._encode_application_enumerated(device.segmentation_supported)
            + self._encode_application_unsigned(device.vendor_identifier)
        )

    def _build_bvlc(self, *, function: int, npdu: bytes) -> bytes:
        total_length = 4 + len(npdu)
        return bytes([_BVLC_TYPE_BACNET_IP, function]) + struct.pack(">H", total_length) + npdu

    def _parse_who_is_limits(self, payload: bytes) -> tuple[int | None, int | None]:
        if not payload:
            return None, None

        lower_limit, offset = self._decode_application_unsigned(payload, 0)
        if lower_limit is None:
            return None, None
        upper_limit, _ = self._decode_application_unsigned(payload, offset)
        return lower_limit, upper_limit

    def _parse_property_reference(self, payload: bytes) -> tuple[int, int, int] | None:
        object_identifier, offset = self._decode_context_object_identifier(payload, 0, _CONTEXT_TAG_OBJECT_IDENTIFIER)
        if object_identifier is None:
            return None

        property_identifier, offset = self._decode_context_unsigned(payload, offset, _CONTEXT_TAG_PROPERTY_IDENTIFIER)
        if property_identifier is None:
            return None

        if offset < len(payload) and self._is_context_tag(payload[offset], _CONTEXT_TAG_PROPERTY_ARRAY_INDEX):
            _array_index, offset = self._decode_context_unsigned(payload, offset, _CONTEXT_TAG_PROPERTY_ARRAY_INDEX)

        if offset != len(payload):
            return None

        object_type, instance = object_identifier
        return object_type, instance, property_identifier

    def _parse_write_property_request(
        self,
        payload: bytes,
    ) -> tuple[int, int, int, bytes] | None:
        object_identifier, offset = self._decode_context_object_identifier(payload, 0, _CONTEXT_TAG_OBJECT_IDENTIFIER)
        if object_identifier is None:
            return None

        property_identifier, offset = self._decode_context_unsigned(payload, offset, _CONTEXT_TAG_PROPERTY_IDENTIFIER)
        if property_identifier is None:
            return None

        if offset < len(payload) and self._is_context_tag(payload[offset], _CONTEXT_TAG_PROPERTY_ARRAY_INDEX):
            _array_index, offset = self._decode_context_unsigned(payload, offset, _CONTEXT_TAG_PROPERTY_ARRAY_INDEX)

        if offset >= len(payload) or payload[offset] != self._encode_opening_tag(_CONTEXT_TAG_PROPERTY_VALUE)[0]:
            return None
        offset += 1

        property_value_end = payload.find(self._encode_closing_tag(_CONTEXT_TAG_PROPERTY_VALUE), offset)
        if property_value_end == -1:
            return None

        property_value = payload[offset:property_value_end]
        object_type, instance = object_identifier
        return object_type, instance, property_identifier, property_value

    def _encode_application_unsigned(self, value: int) -> bytes:
        encoded_value = self._encode_unsigned_value(value)
        return self._encode_tag_header(_APPLICATION_TAG_UNSIGNED, is_context=False, length=len(encoded_value)) + encoded_value

    def _encode_application_enumerated(self, value: int) -> bytes:
        encoded_value = self._encode_unsigned_value(value)
        return self._encode_tag_header(_APPLICATION_TAG_ENUMERATED, is_context=False, length=len(encoded_value)) + encoded_value

    def _encode_application_real(self, value: float) -> bytes:
        return self._encode_tag_header(_APPLICATION_TAG_REAL, is_context=False, length=_APPLICATION_REAL_LENGTH) + struct.pack(">f", value)

    def _encode_application_character_string(self, value: str) -> bytes:
        encoded_value = b"\x00" + value.encode("ascii")
        return self._encode_tag_header(_APPLICATION_TAG_CHARACTER_STRING, is_context=False, length=len(encoded_value)) + encoded_value

    def _encode_application_bit_string(self, value: bytes) -> bytes:
        encoded_value = b"\x00" + value
        return self._encode_tag_header(_APPLICATION_TAG_BIT_STRING, is_context=False, length=len(encoded_value)) + encoded_value

    def _encode_application_object_identifier(self, object_type: int, instance: int) -> bytes:
        encoded_value = struct.pack(">I", (object_type << 22) | instance)
        return self._encode_tag_header(_APPLICATION_TAG_OBJECT_IDENTIFIER, is_context=False, length=len(encoded_value)) + encoded_value

    def _encode_context_unsigned(self, tag_number: int, value: int) -> bytes:
        encoded_value = self._encode_unsigned_value(value)
        return self._encode_tag_header(tag_number, is_context=True, length=len(encoded_value)) + encoded_value

    def _encode_context_object_identifier(self, tag_number: int, object_type: int, instance: int) -> bytes:
        encoded_value = struct.pack(">I", (object_type << 22) | instance)
        return self._encode_tag_header(tag_number, is_context=True, length=len(encoded_value)) + encoded_value

    def _encode_opening_tag(self, tag_number: int) -> bytes:
        return bytes([(tag_number << 4) | 0x0E])

    def _encode_closing_tag(self, tag_number: int) -> bytes:
        return bytes([(tag_number << 4) | 0x0F])

    def _encode_tag_header(self, tag_number: int, *, is_context: bool, length: int) -> bytes:
        class_bit = _CONTEXT_CLASS_BIT if is_context else 0x00
        if length <= _MAX_INLINE_LENGTH:
            return bytes([(tag_number << 4) | class_bit | length])
        return bytes([(tag_number << 4) | class_bit | _EXTENDED_LENGTH_SENTINEL, length])

    def _encode_unsigned_value(self, value: int) -> bytes:
        if value == 0:
            return b"\x00"
        byte_length = max(1, (value.bit_length() + 7) // 8)
        return value.to_bytes(byte_length, byteorder="big")

    def _decode_application_real(self, payload: bytes) -> float | None:
        if len(payload) != _APPLICATION_REAL_TOTAL_SIZE:
            return None
        if payload[0] != self._encode_tag_header(_APPLICATION_TAG_REAL, is_context=False, length=_APPLICATION_REAL_LENGTH)[0]:
            return None
        return struct.unpack(">f", payload[1:_APPLICATION_REAL_TOTAL_SIZE])[0]

    def _decode_application_unsigned(self, payload: bytes, offset: int) -> tuple[int | None, int]:
        if len(payload) <= offset:
            return None, offset

        tag_byte = payload[offset]
        if (tag_byte >> 4) != _APPLICATION_TAG_UNSIGNED or tag_byte & _CONTEXT_CLASS_BIT:
            return None, offset
        length, header_size = self._decode_tag_length(payload, offset)
        value_offset = offset + header_size
        value_end = value_offset + length
        if len(payload) < value_end:
            return None, offset

        return int.from_bytes(payload[value_offset:value_end], byteorder="big"), value_end

    def _decode_context_unsigned(self, payload: bytes, offset: int, tag_number: int) -> tuple[int | None, int]:
        if len(payload) <= offset or not self._is_context_tag(payload[offset], tag_number):
            return None, offset

        length, header_size = self._decode_tag_length(payload, offset)
        value_offset = offset + header_size
        value_end = value_offset + length
        if len(payload) < value_end:
            return None, offset

        return int.from_bytes(payload[value_offset:value_end], byteorder="big"), value_end

    def _decode_context_object_identifier(
        self,
        payload: bytes,
        offset: int,
        tag_number: int,
    ) -> tuple[tuple[int, int] | None, int]:
        if len(payload) <= offset or not self._is_context_tag(payload[offset], tag_number):
            return None, offset

        length, header_size = self._decode_tag_length(payload, offset)
        if length != _APPLICATION_REAL_LENGTH:
            return None, offset

        value_offset = offset + header_size
        value_end = value_offset + length
        if len(payload) < value_end:
            return None, offset

        raw_value = struct.unpack(">I", payload[value_offset:value_end])[0]
        return (raw_value >> 22, raw_value & 0x3FFFFF), value_end

    def _decode_tag_length(self, payload: bytes, offset: int) -> tuple[int, int]:
        length = payload[offset] & 0x07
        if length != _EXTENDED_LENGTH_SENTINEL:
            return length, 1
        return payload[offset + 1], 2

    def _is_context_tag(self, tag_byte: int, tag_number: int) -> bool:
        return (tag_byte >> 4) == tag_number and (tag_byte & _CONTEXT_CLASS_BIT) == _CONTEXT_CLASS_BIT
