import importlib  # noqa: D100
import logging
import threading
import time
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from types import ModuleType

    from decimalog.logger import CustomLogger


class Starter:
    """Starter class to initialize and start protocol servers."""

    def __init__(self, protocol: str, port: int, delay: int) -> None:
        """Initialize the Starter with the specified protocol, port, and delay."""
        self.logger: CustomLogger = cast("CustomLogger", logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}"))

        self._protocol: str = protocol
        self._port: int = port
        self._delay: int = delay

    def start_server(self) -> None:
        """Start the specified protocol server after a delay."""
        module: ModuleType = importlib.import_module(f"cursusd.{self._protocol.lower()}.server")
        server_class = getattr(module, f"{self._protocol.capitalize()}Server")
        server = server_class(ip="localhost", port=self._port)
        server_thread = threading.Thread(target=server.start, name=f"{self._protocol.capitalize()}Server", daemon=True)
        server_thread.start()
        self.logger.info(f"[+] Started {self._protocol} server on port {self._port}")
        time.sleep(self._delay)
