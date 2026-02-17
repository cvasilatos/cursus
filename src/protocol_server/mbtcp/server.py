import logging
from typing import cast

from pymodbus.datastore import ModbusDeviceContext, ModbusSequentialDataBlock
from pymodbus.datastore.context import ModbusServerContext
from pymodbus.pdu.device import ModbusDeviceIdentification
from pymodbus.server import StartTcpServer

from protocol_server.cfg.log_configuration import CustomLogger


class MbtcpServer:
    def __init__(self, ip: str, port: int, size: int = 32000) -> None:
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
        self.logger.info(f"Starting Modbus TCP server at {self._ip}:{self._port}")
        StartTcpServer(context=self._context, identity=self._identity, address=(self._ip, self._port))


if __name__ == "__main__":
    CustomLogger.setup_logging("logs", "protocol_server", level="TRACE")
    server = MbtcpServer(ip="127.0.0.1", port=5020, size=32000)
    server.start()
