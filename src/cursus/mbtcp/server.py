import asyncio
import logging
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from decima.logger import CustomLogger
from pymodbus.datastore import ModbusDeviceContext, ModbusSequentialDataBlock
from pymodbus.datastore.context import ModbusServerContext
from pymodbus.pdu.device import ModbusDeviceIdentification
from pymodbus.server import ModbusTcpServer


class MbtcpServer:
    """Modbus TCP server implementation using pymodbus."""

    def __init__(self, ip: str, port: int, size: int = 32000) -> None:
        """Initialize the Modbus TCP server with the specified IP, port, and data block size.

        Args:
            ip: The IP address to bind the server to (e.g., "127.0.0.1" or "0.0.0.0").
            port: The TCP port number to listen on (default Modbus port is 502).
            size: The size of the data blocks in registers. Defaults to 32000.
                  This size applies to all four Modbus data tables: Input Registers (IR),
                  Holding Registers (HR), Discrete Inputs (DI), and Coils (CO).

        """
        self.logger: CustomLogger = cast("CustomLogger", logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}"))
        self._ip: str = ip
        self._port: int = port

        # SequentialDataBlock to cover 0..size-1 for all tables
        zero_ir = ModbusSequentialDataBlock(1, list(range(size)))
        zero_hr = ModbusSequentialDataBlock(1, list(range(size)))
        zero_di = ModbusSequentialDataBlock(1, list(range(size)))
        zero_co = ModbusSequentialDataBlock(1, list(range(size)))

        store = ModbusDeviceContext(ir=zero_ir, hr=zero_hr, di=zero_di, co=zero_co)

        self._context = ModbusServerContext(devices=store, single=True)

        self._identity = ModbusDeviceIdentification()
        self._identity.VendorName = "WAGO"
        self._identity.ProductCode = "750-881"
        self._identity.VendorUrl = "https://www.wago.com"
        self._identity.ProductName = "ETHERNET Programmable Fieldbus Controller"
        self._identity.ModelName = "PFC200"
        self._identity.MajorMinorRevision = "03.01.02"
        self._server: ModbusTcpServer | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    def start(self) -> None:
        """Start the Modbus TCP server.

        Starts the Modbus TCP server and blocks indefinitely, listening for
        incoming client connections on the configured IP address and port.
        This method will not return until the server is stopped externally.

        Note:
            This is a blocking call. The server will run continuously until
            interrupted (e.g., by Ctrl+C or external signal).

        """
        self.logger.info(f"Starting Modbus TCP server at {self._ip}:{self._port}")
        loop = asyncio.new_event_loop()
        self._loop = loop

        try:
            asyncio.set_event_loop(loop)
            self._server = loop.run_until_complete(self._create_server())
            loop.run_until_complete(self._server.serve_forever())
        finally:
            asyncio.set_event_loop(None)
            loop.close()
            self._server = None
            self._loop = None

    def stop(self) -> None:
        """Stop the Modbus TCP server when it is running."""
        if self._server is None or self._loop is None:
            return

        self.logger.info(f"Stopping Modbus TCP server at {self._ip}:{self._port}")
        shutdown = asyncio.run_coroutine_threadsafe(self._server.shutdown(), self._loop)
        shutdown.result(timeout=5)

    async def _create_server(self) -> ModbusTcpServer:
        """Create the Modbus server while an event loop is active."""
        return ModbusTcpServer(context=self._context, identity=self._identity, address=(self._ip, self._port))
