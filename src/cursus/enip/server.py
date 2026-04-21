import logging
import socket
import socketserver
import struct
import threading
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from decima.logger import CustomLogger


_ENCAPSULATION_HEADER = struct.Struct("<HHII8sI")

_COMMAND_LIST_SERVICES = 0x0004
_COMMAND_LIST_IDENTITY = 0x0063
_COMMAND_LIST_INTERFACES = 0x0064
_COMMAND_REGISTER_SESSION = 0x0065
_COMMAND_UNREGISTER_SESSION = 0x0066
_COMMAND_SEND_RR_DATA = 0x006F

_ENCAP_STATUS_SUCCESS = 0x0000
_ENCAP_STATUS_INVALID_COMMAND = 0x0001
_ENCAP_STATUS_INCORRECT_DATA = 0x0003
_ENCAP_STATUS_INVALID_SESSION = 0x0064

_CPF_ITEM_NULL_ADDRESS = 0x0000
_CPF_ITEM_UNCONNECTED_DATA = 0x00B2
_LIST_SERVICES_ITEM = 0x0100
_LIST_IDENTITY_ITEM = 0x000C
_PROTOCOL_VERSION = 1
_REGISTER_SESSION_PAYLOAD_SIZE = 4
_SEND_RR_DATA_HEADER_SIZE = 8
_CIP_REQUEST_HEADER_SIZE = 2
_ASSEMBLY_DATA_ATTRIBUTE = 3
_BIND_ALL_INTERFACES = socket.inet_ntoa(struct.pack("!I", socket.INADDR_ANY))
_LOOPBACK_ADDRESS = "127.0.0.1"

_CIP_SERVICE_GET_ATTRIBUTES_ALL = 0x01
_CIP_SERVICE_GET_ATTRIBUTE_SINGLE = 0x0E
_CIP_SERVICE_SET_ATTRIBUTE_SINGLE = 0x10

_CIP_STATUS_SUCCESS = 0x00
_CIP_STATUS_PATH_SEGMENT_ERROR = 0x04
_CIP_STATUS_PATH_DESTINATION_UNKNOWN = 0x05
_CIP_STATUS_SERVICE_NOT_SUPPORTED = 0x08
_CIP_STATUS_ATTRIBUTE_NOT_SETTABLE = 0x0E
_CIP_STATUS_ATTRIBUTE_NOT_SUPPORTED = 0x14
_CIP_STATUS_NOT_ENOUGH_DATA = 0x13

_IDENTITY_CLASS = 0x01
_ASSEMBLY_CLASS = 0x04
_IDENTITY_ATTR_VENDOR_ID = 1
_IDENTITY_ATTR_DEVICE_TYPE = 2
_IDENTITY_ATTR_PRODUCT_CODE = 3
_IDENTITY_ATTR_REVISION = 4
_IDENTITY_ATTR_STATUS = 5
_IDENTITY_ATTR_SERIAL_NUMBER = 6
_IDENTITY_ATTR_PRODUCT_NAME = 7
_IDENTITY_ATTR_STATE = 8
_IDENTITY_ATTRIBUTES_ALL = (
    _IDENTITY_ATTR_VENDOR_ID,
    _IDENTITY_ATTR_DEVICE_TYPE,
    _IDENTITY_ATTR_PRODUCT_CODE,
    _IDENTITY_ATTR_REVISION,
    _IDENTITY_ATTR_STATUS,
    _IDENTITY_ATTR_SERIAL_NUMBER,
    _IDENTITY_ATTR_PRODUCT_NAME,
)
_SEGMENT_TYPE_BY_CODE = {
    0x20: "class",
    0x21: "class",
    0x22: "class",
    0x24: "instance",
    0x25: "instance",
    0x26: "instance",
    0x30: "attribute",
    0x31: "attribute",
    0x32: "attribute",
}


@dataclass(slots=True)
class EnipIdentity:
    """Identity object values returned by the EtherNet/IP emulator."""

    vendor_id: int = 1
    device_type: int = 12
    product_code: int = 65001
    revision_major: int = 1
    revision_minor: int = 0
    status: int = 0x0030
    serial_number: int = 0xC0DA2026
    product_name: str = "1756-EN2T/A"
    state: int = 0x03


@dataclass(slots=True)
class EnipServerConfig:
    """Configuration for the EtherNet/IP server."""

    identity: EnipIdentity = field(default_factory=EnipIdentity)
    assemblies: dict[int, bytes] = field(
        default_factory=lambda: {
            100: bytes(32),
            101: bytes(32),
            150: bytes(32),
        }
    )


@dataclass(slots=True)
class _EncapsulationFrame:
    command: int
    session_handle: int
    sender_context: bytes
    options: int
    payload: bytes


class _EnipTcpServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True
    block_on_close = False
    protocol: "EnipServer"


class _EnipRequestHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        server = cast("_EnipTcpServer", self.server)
        protocol = server.protocol
        buffer = b""
        session_handles: set[int] = set()

        try:
            while True:
                chunk = self.request.recv(4096)
                if not chunk:
                    break

                buffer += chunk
                while len(buffer) >= _ENCAPSULATION_HEADER.size:
                    command, length, session_handle, _status, sender_context, options = _ENCAPSULATION_HEADER.unpack(buffer[: _ENCAPSULATION_HEADER.size])
                    frame_size = _ENCAPSULATION_HEADER.size + length
                    if len(buffer) < frame_size:
                        break

                    frame = _EncapsulationFrame(
                        command=command,
                        session_handle=session_handle,
                        sender_context=sender_context,
                        options=options,
                        payload=buffer[_ENCAPSULATION_HEADER.size : frame_size],
                    )
                    buffer = buffer[frame_size:]

                    response = protocol.handle_frame(
                        frame=frame,
                        connection_sessions=session_handles,
                    )
                    if response:
                        self.request.sendall(response)
        except OSError:
            protocol.logger.debug("EtherNet/IP client disconnected unexpectedly")
        finally:
            protocol.release_sessions(session_handles)


class EnipServer:
    """EtherNet/IP explicit-message server implementation."""

    def __init__(
        self,
        ip: str,
        port: int = 44818,
        config: EnipServerConfig | None = None,
    ) -> None:
        """Initialize the EtherNet/IP emulator."""
        logger_name = f"{self.__class__.__module__}.{self.__class__.__name__}"
        self.logger: CustomLogger = cast("CustomLogger", logging.getLogger(logger_name))
        self._ip = ip
        self._port = port
        self._config = config or EnipServerConfig()
        self._server: _EnipTcpServer | None = None

        self._session_lock = threading.Lock()
        self._next_session_handle = 1
        self._active_sessions: set[int] = set()

        self._assembly_lock = threading.Lock()
        self._assemblies = {instance: bytes(data) for instance, data in self._config.assemblies.items()}

    def start(self) -> None:
        """Start the EtherNet/IP TCP server and block until stopped."""
        self.logger.info(f"Starting EtherNet/IP server at {self._ip}:{self._port}")
        server = _EnipTcpServer((self._ip, self._port), _EnipRequestHandler)
        server.protocol = self
        self._server = server

        try:
            server.serve_forever()
        finally:
            server.server_close()
            self._server = None

    def stop(self) -> None:
        """Stop the EtherNet/IP server when it is running."""
        if self._server is None:
            return

        self.logger.info(f"Stopping EtherNet/IP server at {self._ip}:{self._port}")
        self._server.shutdown()

    def set_assembly_data(self, instance: int, data: bytes | bytearray) -> None:
        """Replace the raw bytes for an Assembly object instance."""
        with self._assembly_lock:
            self._assemblies[instance] = bytes(data)

    def get_assembly_data(self, instance: int) -> bytes:
        """Return the raw bytes for an Assembly object instance."""
        with self._assembly_lock:
            return self._assemblies[instance]

    def release_sessions(self, sessions: set[int]) -> None:
        """Remove all session handles that belonged to a closed connection."""
        if not sessions:
            return

        with self._session_lock:
            self._active_sessions.difference_update(sessions)

    def handle_frame(
        self,
        *,
        frame: _EncapsulationFrame,
        connection_sessions: set[int],
    ) -> bytes | None:
        """Handle a single EtherNet/IP encapsulation command."""
        if frame.options != 0:
            return self._build_encapsulation_response(
                command=frame.command,
                session_handle=frame.session_handle,
                sender_context=frame.sender_context,
                status=_ENCAP_STATUS_INCORRECT_DATA,
            )

        if frame.command == _COMMAND_REGISTER_SESSION:
            return self._handle_register_session(
                sender_context=frame.sender_context,
                payload=frame.payload,
                connection_sessions=connection_sessions,
            )

        if frame.command == _COMMAND_UNREGISTER_SESSION:
            self._unregister_session(frame.session_handle, connection_sessions)
            return None

        response_session_handle = frame.session_handle
        response_payload = b""
        response_status = _ENCAP_STATUS_SUCCESS

        if frame.command == _COMMAND_LIST_SERVICES:
            response_session_handle = 0
            response_payload = self._build_list_services_payload()
        elif frame.command == _COMMAND_LIST_IDENTITY:
            response_session_handle = 0
            response_payload = self._build_list_identity_payload()
        elif frame.command == _COMMAND_LIST_INTERFACES:
            response_session_handle = 0
            response_payload = struct.pack("<H", 0)
        elif frame.command == _COMMAND_SEND_RR_DATA:
            if not self._session_is_active(frame.session_handle):
                response_status = _ENCAP_STATUS_INVALID_SESSION
            else:
                cip_response = self._handle_send_rr_data(frame.payload)
                if cip_response is None:
                    response_status = _ENCAP_STATUS_INCORRECT_DATA
                else:
                    response_payload = cip_response
        else:
            response_status = _ENCAP_STATUS_INVALID_COMMAND

        return self._build_encapsulation_response(
            command=frame.command,
            session_handle=response_session_handle,
            sender_context=frame.sender_context,
            payload=response_payload,
            status=response_status,
        )

    def _build_encapsulation_response(
        self,
        *,
        command: int,
        session_handle: int,
        sender_context: bytes,
        payload: bytes = b"",
        status: int = _ENCAP_STATUS_SUCCESS,
    ) -> bytes:
        return (
            _ENCAPSULATION_HEADER.pack(
                command,
                len(payload),
                session_handle,
                status,
                sender_context,
                0,
            )
            + payload
        )

    def _handle_register_session(
        self,
        *,
        sender_context: bytes,
        payload: bytes,
        connection_sessions: set[int],
    ) -> bytes:
        if len(payload) != _REGISTER_SESSION_PAYLOAD_SIZE:
            return self._build_encapsulation_response(
                command=_COMMAND_REGISTER_SESSION,
                session_handle=0,
                sender_context=sender_context,
                status=_ENCAP_STATUS_INCORRECT_DATA,
            )

        protocol_version, option_flags = struct.unpack("<HH", payload)
        if protocol_version != _PROTOCOL_VERSION or option_flags != 0:
            return self._build_encapsulation_response(
                command=_COMMAND_REGISTER_SESSION,
                session_handle=0,
                sender_context=sender_context,
                status=_ENCAP_STATUS_INCORRECT_DATA,
            )

        with self._session_lock:
            session_handle = self._next_session_handle
            self._next_session_handle += 1
            self._active_sessions.add(session_handle)
            connection_sessions.add(session_handle)

        return self._build_encapsulation_response(
            command=_COMMAND_REGISTER_SESSION,
            session_handle=session_handle,
            sender_context=sender_context,
            payload=payload,
        )

    def _unregister_session(self, session_handle: int, connection_sessions: set[int]) -> None:
        with self._session_lock:
            self._active_sessions.discard(session_handle)
            connection_sessions.discard(session_handle)

    def _session_is_active(self, session_handle: int) -> bool:
        with self._session_lock:
            return session_handle in self._active_sessions

    def _build_list_services_payload(self) -> bytes:
        service_name = b"Communications".ljust(16, b"\x00")
        item = struct.pack(
            "<HHHH16s",
            _LIST_SERVICES_ITEM,
            20,
            _PROTOCOL_VERSION,
            0x0020,
            service_name,
        )
        return struct.pack("<H", 1) + item

    def _build_list_identity_payload(self) -> bytes:
        identity = self._config.identity
        product_name = identity.product_name.encode("ascii")
        address = self._ip if self._ip != _BIND_ALL_INTERFACES else _LOOPBACK_ADDRESS
        socket_address = struct.pack(
            ">HH4s8s",
            socket.AF_INET,
            self._port,
            socket.inet_aton(address),
            b"\x00" * 8,
        )
        item_data = (
            struct.pack("<H", _PROTOCOL_VERSION)
            + socket_address
            + struct.pack(
                "<HHHBBHI",
                identity.vendor_id,
                identity.device_type,
                identity.product_code,
                identity.revision_major,
                identity.revision_minor,
                identity.status,
                identity.serial_number,
            )
            + struct.pack("<B", len(product_name))
            + product_name
            + struct.pack("<B", identity.state)
        )
        item_header = struct.pack("<HH", _LIST_IDENTITY_ITEM, len(item_data))
        return struct.pack("<H", 1) + item_header + item_data

    def _handle_send_rr_data(self, payload: bytes) -> bytes | None:
        if len(payload) < _SEND_RR_DATA_HEADER_SIZE:
            return None

        interface_handle, timeout, item_count = struct.unpack_from("<IHH", payload, 0)
        if interface_handle != 0:
            return None

        offset = 8
        cip_request = None
        for _ in range(item_count):
            if len(payload) < offset + 4:
                return None

            item_type, item_length = struct.unpack_from("<HH", payload, offset)
            offset += 4
            if len(payload) < offset + item_length:
                return None

            item_data = payload[offset : offset + item_length]
            offset += item_length

            if item_type == _CPF_ITEM_UNCONNECTED_DATA:
                cip_request = item_data

        if cip_request is None:
            return None

        cip_response = self._handle_cip_request(cip_request)
        return struct.pack("<IHH", 0, timeout, 2) + struct.pack("<HH", _CPF_ITEM_NULL_ADDRESS, 0) + struct.pack("<HH", _CPF_ITEM_UNCONNECTED_DATA, len(cip_response)) + cip_response

    def _handle_cip_request(self, request: bytes) -> bytes:  # noqa: PLR0911
        if len(request) < _CIP_REQUEST_HEADER_SIZE:
            return self._build_cip_response(service=0, status=_CIP_STATUS_NOT_ENOUGH_DATA)

        service = request[0]
        path_words = request[1]
        path_length = path_words * 2
        if len(request) < _CIP_REQUEST_HEADER_SIZE + path_length:
            return self._build_cip_response(service=service, status=_CIP_STATUS_NOT_ENOUGH_DATA)

        try:
            class_code, instance, attribute = self._parse_cip_path(request[_CIP_REQUEST_HEADER_SIZE : _CIP_REQUEST_HEADER_SIZE + path_length])
        except ValueError:
            return self._build_cip_response(service=service, status=_CIP_STATUS_PATH_SEGMENT_ERROR)

        request_data = request[_CIP_REQUEST_HEADER_SIZE + path_length :]
        if service == _CIP_SERVICE_GET_ATTRIBUTES_ALL:
            response_data, status = self._get_attributes_all(
                class_code=class_code,
                instance=instance,
            )
            return self._build_cip_response(service=service, status=status, data=response_data)

        if service == _CIP_SERVICE_GET_ATTRIBUTE_SINGLE:
            if attribute is None:
                return self._build_cip_response(
                    service=service,
                    status=_CIP_STATUS_PATH_DESTINATION_UNKNOWN,
                )

            response_data, status = self._get_attribute(
                class_code=class_code,
                instance=instance,
                attribute=attribute,
            )
            return self._build_cip_response(service=service, status=status, data=response_data)

        if service == _CIP_SERVICE_SET_ATTRIBUTE_SINGLE:
            if attribute is None:
                return self._build_cip_response(service=service, status=_CIP_STATUS_PATH_DESTINATION_UNKNOWN)

            status = self._set_attribute(
                class_code=class_code,
                instance=instance,
                attribute=attribute,
                value=request_data,
            )
            return self._build_cip_response(service=service, status=status)

        return self._build_cip_response(
            service=service,
            status=_CIP_STATUS_SERVICE_NOT_SUPPORTED,
        )

    def _build_cip_response(
        self,
        *,
        service: int,
        status: int,
        data: bytes = b"",
    ) -> bytes:
        return bytes([service | 0x80, 0x00, status, 0x00]) + data

    def _get_attributes_all(self, *, class_code: int, instance: int) -> tuple[bytes, int]:
        if class_code == _IDENTITY_CLASS and instance == 1:
            return (
                b"".join(self._pack_identity_attribute(attribute) for attribute in _IDENTITY_ATTRIBUTES_ALL),
                _CIP_STATUS_SUCCESS,
            )

        if class_code == _ASSEMBLY_CLASS:
            return self._get_attribute(
                class_code=class_code,
                instance=instance,
                attribute=_ASSEMBLY_DATA_ATTRIBUTE,
            )

        return b"", _CIP_STATUS_PATH_DESTINATION_UNKNOWN

    def _get_attribute(
        self,
        *,
        class_code: int,
        instance: int,
        attribute: int,
    ) -> tuple[bytes, int]:
        if class_code == _IDENTITY_CLASS and instance == 1:
            try:
                return self._pack_identity_attribute(attribute), _CIP_STATUS_SUCCESS
            except KeyError:
                return b"", _CIP_STATUS_ATTRIBUTE_NOT_SUPPORTED

        if class_code == _ASSEMBLY_CLASS:
            if attribute != _ASSEMBLY_DATA_ATTRIBUTE:
                return b"", _CIP_STATUS_ATTRIBUTE_NOT_SUPPORTED

            with self._assembly_lock:
                data = self._assemblies.get(instance)

            if data is None:
                return b"", _CIP_STATUS_PATH_DESTINATION_UNKNOWN

            return data, _CIP_STATUS_SUCCESS

        return b"", _CIP_STATUS_PATH_DESTINATION_UNKNOWN

    def _set_attribute(
        self,
        *,
        class_code: int,
        instance: int,
        attribute: int,
        value: bytes,
    ) -> int:
        if class_code == _ASSEMBLY_CLASS:
            if attribute != _ASSEMBLY_DATA_ATTRIBUTE:
                return _CIP_STATUS_ATTRIBUTE_NOT_SUPPORTED

            with self._assembly_lock:
                if instance not in self._assemblies:
                    return _CIP_STATUS_PATH_DESTINATION_UNKNOWN

                self._assemblies[instance] = bytes(value)
                return _CIP_STATUS_SUCCESS

        if class_code == _IDENTITY_CLASS and instance == 1:
            return _CIP_STATUS_ATTRIBUTE_NOT_SETTABLE

        return _CIP_STATUS_PATH_DESTINATION_UNKNOWN

    def _pack_identity_attribute(self, attribute: int) -> bytes:
        identity = self._config.identity
        product_name = identity.product_name.encode("ascii")
        attributes = {
            _IDENTITY_ATTR_VENDOR_ID: struct.pack("<H", identity.vendor_id),
            _IDENTITY_ATTR_DEVICE_TYPE: struct.pack("<H", identity.device_type),
            _IDENTITY_ATTR_PRODUCT_CODE: struct.pack("<H", identity.product_code),
            _IDENTITY_ATTR_REVISION: struct.pack("<BB", identity.revision_major, identity.revision_minor),
            _IDENTITY_ATTR_STATUS: struct.pack("<H", identity.status),
            _IDENTITY_ATTR_SERIAL_NUMBER: struct.pack("<I", identity.serial_number),
            _IDENTITY_ATTR_PRODUCT_NAME: struct.pack("<B", len(product_name)) + product_name,
            _IDENTITY_ATTR_STATE: struct.pack("<B", identity.state),
        }

        try:
            return attributes[attribute]
        except KeyError:
            raise KeyError(attribute) from None

    def _parse_cip_path(self, path: bytes) -> tuple[int, int, int | None]:
        class_code: int | None = None
        instance: int | None = None
        attribute: int | None = None
        offset = 0

        while offset < len(path):
            segment = path[offset]
            offset += 1

            if segment == 0:
                continue

            value, offset = self._read_path_value(path=path, offset=offset, segment=segment)
            segment_type = _SEGMENT_TYPE_BY_CODE.get(segment)
            if segment_type is None:
                raise ValueError(segment)

            if segment_type == "class":
                class_code = value
            elif segment_type == "instance":
                instance = value
            else:
                attribute = value

        if class_code is None or instance is None:
            raise ValueError("Missing class or instance path segment")

        return class_code, instance, attribute

    def _read_path_value(self, *, path: bytes, offset: int, segment: int) -> tuple[int, int]:
        if segment in {0x20, 0x24, 0x30}:
            if offset >= len(path):
                raise ValueError(segment)
            return path[offset], offset + 1

        if segment in {0x21, 0x25, 0x31}:
            if offset + 2 > len(path):
                raise ValueError(segment)
            return struct.unpack_from("<H", path, offset)[0], offset + 2

        if segment in {0x22, 0x26, 0x32}:
            if offset + 4 > len(path):
                raise ValueError(segment)
            return struct.unpack_from("<I", path, offset)[0], offset + 4

        raise ValueError(segment)
