import logging  # noqa: D100
from typing import cast

import snap7
from decimalog.logger import CustomLogger


class S7commServer:
    """S7comm server implementation using snap7."""

    def __init__(self, ip: str, port: int, size: int = 32000) -> None:
        """Initialize the S7comm server with the specified IP, port, and data block size."""
        self.logger: CustomLogger = cast("CustomLogger", logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}"))
        self._ip: str = ip
        self._port: int = port
        self._size: int = size

        # Create the snap7 server instance
        self._server = snap7.Server()

        # Register data areas: DB, PA, PE, MK, TM, CT
        # Note: snap7 maintains internal references to these byte arrays
        # DB1: Data Block 1
        db1_data = bytearray(size)
        self._server.register_area(snap7.SrvArea.DB, 1, db1_data)

        # PA: Process outputs
        pa_data = bytearray(size)
        self._server.register_area(snap7.SrvArea.PA, 0, pa_data)

        # PE: Process inputs
        pe_data = bytearray(size)
        self._server.register_area(snap7.SrvArea.PE, 0, pe_data)

        # MK: Merkers memory
        mk_data = bytearray(size)
        self._server.register_area(snap7.SrvArea.MK, 0, mk_data)

        # Timer data area
        tm_data = bytearray(size)
        self._server.register_area(snap7.SrvArea.TM, 0, tm_data)

        # Counter data area
        ct_data = bytearray(size)
        self._server.register_area(snap7.SrvArea.CT, 0, ct_data)

    def start(self) -> None:
        """Start the S7comm server."""
        self.logger.info(f"Starting S7comm server at {self._ip}:{self._port}")
        # Bind to specific IP address and TCP port
        self._server.start_to(self._ip, tcpport=self._port)
        # Keep the server running
        while True:
            self._server.pick_event()


if __name__ == "__main__":
    CustomLogger.setup_logging("logs", "cursusd", level="TRACE")
    server = S7commServer(ip="127.0.0.1", port=5102, size=32000)
    server.start()
