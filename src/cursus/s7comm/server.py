import logging
from ctypes import c_byte
from typing import TYPE_CHECKING, cast

import snap7

if TYPE_CHECKING:
    from decima.logger import CustomLogger


class S7commServer:
    """S7comm server implementation using snap7."""

    def __init__(self, ip: str, port: int, size: int = 1024) -> None:
        """Initialize the S7comm server with the specified IP, port, and data block size.

        Args:
            ip: The IP address to bind the server to (e.g., "127.0.0.1" or "0.0.0.0").
            port: The TCP port number to listen on (default S7comm port is 102).
            size: The size of the memory areas in bytes. Defaults to 32000.
                  This size applies to all S7 data areas: Data Block (DB1), Process
                  Outputs (PA), Process Inputs (PE), Merkers memory (MK), Timers (TM),
                  and Counters (CT).

        """
        self.logger: CustomLogger = cast("CustomLogger", logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}"))
        self._ip: str = ip
        self._port: int = port
        self._size: int = size

        # Create the snap7 server instance
        self._server = snap7.Server()

        # Register data areas: DB, PA, PE, MK, TM, CT
        # Use ctypes arrays for compatibility with snap7 C API
        # DB1: Data Block 1
        db1_data = (c_byte * 64)()
        error = self._server.register_area(snap7.SrvArea.DB, 0, db1_data)
        self.logger.error(
            f"Initializing S7comm server with IP: {ip}, Port: {port}, Data Block Size: {size} bytes: {error}",
        )

        # PA: Process outputs
        pa_data = (c_byte * size)()
        self._server.register_area(snap7.SrvArea.PA, 0, pa_data)

        # PE: Process inputs
        pe_data = (c_byte * size)()
        self._server.register_area(snap7.SrvArea.PE, 0, pe_data)

        # MK: Merkers memory
        mk_data = (c_byte * size)()
        self._server.register_area(snap7.SrvArea.MK, 0, mk_data)

        # Timer data area
        tm_data = (c_byte * size)()
        self._server.register_area(snap7.SrvArea.TM, 0, tm_data)

        # Counter data area
        ct_data = (c_byte * size)()
        self._server.register_area(snap7.SrvArea.CT, 0, ct_data)

    def start(self) -> None:
        """Start the S7comm server.

        Starts the S7comm server and blocks indefinitely, listening for
        incoming client connections on the configured IP address and port.
        The server continuously processes events using the snap7 event loop.

        Note:
            This is a blocking call. The server will run continuously until
            interrupted (e.g., by Ctrl+C or external signal).

        """
        self.logger.info(f"Starting S7comm server at {self._ip}:{self._port}")
        self._server.start_to(self._ip, self._port)
        while True:
            self._server.pick_event()
