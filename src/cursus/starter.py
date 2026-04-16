import importlib
import logging
import threading
import time
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from types import ModuleType

    from decima.logger import CustomLogger


class Starter:
    """Starter class to initialize and start protocol servers."""

    def __init__(self, protocol: str, port: int, delay: int) -> None:
        """Initialize the Starter with the specified protocol, port, and delay.

        Args:
            protocol: The protocol name to use ("mbtcp" or "s7comm").
            port: The port number for the server to bind to.
            delay: The delay in seconds to wait after starting the server.

        """
        self.logger: CustomLogger = cast("CustomLogger", logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}"))

        self._protocol: str = protocol
        self._port: int = port
        self._delay: int = delay

    def start_server(self) -> threading.Thread:
        """Start the specified protocol server after a delay.

        Dynamically imports the server module based on the protocol name,
        creates a server instance, and starts it in a daemon thread. After
        starting the server, it waits for the configured delay period.

        Raises:
            ModuleNotFoundError: If the protocol module cannot be found.
            AttributeError: If the server class does not exist in the module.

        """
        protocol = self._protocol.lower()
        module_name = f"cursus.{protocol}.server"
        class_name = f"{self._protocol.capitalize()}Server"
        if protocol == "dnp3":
            module_name = "cursus.dnp3.docker_server"
            class_name = "Dnp3DockerServer"

        module: ModuleType = importlib.import_module(module_name)
        server_class = getattr(module, class_name)
        server = server_class(ip="127.0.0.1", port=self._port)
        server_thread = threading.Thread(target=server.start, name=f"{self._protocol.capitalize()}Server", daemon=True)
        server_thread.start()
        self.logger.info(f"[+] Started {self._protocol} server on port {self._port}")
        time.sleep(self._delay)
        return server_thread
