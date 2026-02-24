import logging
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from decima.logger import CustomLogger
from pymodbus.datastore import ModbusDeviceContext, ModbusSequentialDataBlock
from pymodbus.datastore.context import ModbusServerContext
from pymodbus.pdu.device import ModbusDeviceIdentification
from pymodbus.server import StartTcpServer


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
        zero_ir = ModbusSequentialDataBlock(0, list(range(size)))
        zero_hr = ModbusSequentialDataBlock(0, list(range(size)))
        zero_di = ModbusSequentialDataBlock(0, list(range(size)))
        zero_co = ModbusSequentialDataBlock(0, list(range(size)))

        store = ModbusDeviceContext(ir=zero_ir, hr=zero_hr, di=zero_di, co=zero_co)

        self._context = ModbusServerContext(devices=store, single=True)

        self._identity = ModbusDeviceIdentification()
        self._identity.VendorName = "WAGO"
        self._identity.ProductCode = "750-881"
        self._identity.VendorUrl = "https://www.wago.com"
        self._identity.ProductName = "ETHERNET Programmable Fieldbus Controller"
        self._identity.ModelName = "PFC200"
        self._identity.MajorMinorRevision = "03.01.02"

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
        StartTcpServer(context=self._context, identity=self._identity, address=(self._ip, self._port))
