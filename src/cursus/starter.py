import importlib
import logging
import threading
import time
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from types import ModuleType

    from decima.logger import CustomLogger


class Starter:
    """Starter class to initialize and start protocol servers."""

    def __init__(self, protocol: str, port: int, delay: int) -> None:
        """Initialize the Starter with the specified protocol, port, and delay.

        Args:
            protocol: The protocol name to use ("mbtcp", "s7comm", or "dnp3").
            port: The port number for the server to bind to.
            delay: The delay in seconds to wait after starting the server.

        """
        self.logger: CustomLogger = cast("CustomLogger", logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}"))

        self._protocol: str = protocol
        self._port: int = port
        self._delay: int = delay
        self._server: Any | None = None
        self._server_thread: threading.Thread | None = None

    def start_server(self) -> threading.Thread:
        """Start the specified protocol server after a delay.

        Dynamically imports the server module based on the protocol name,
        creates a server instance, and starts it in a daemon thread. After
        starting the server, it waits for the configured delay period.

        """
        protocol = self._protocol.lower()
        module_name = f"cursus.{protocol}.server"
        class_name = f"{protocol.capitalize()}Server"
        module: ModuleType = importlib.import_module(module_name)
        server_class = getattr(module, class_name)
        server = server_class(ip="127.0.0.1", port=self._port)
        self._server = server
        server_thread = threading.Thread(target=server.start, name=class_name, daemon=True)
        self._server_thread = server_thread
        server_thread.start()
        self.logger.info(f"[+] Started {self._protocol} server on port {self._port}")
        time.sleep(self._delay)
        return server_thread

    def stop_server(self) -> None:
        """Stop the running protocol server when the backend supports it."""
        if self._server is None:
            self.logger.warning(f"No {self._protocol} server is currently running")
            return

        stop = getattr(self._server, "stop", None)
        if stop is None:
            self.logger.warning(f"{self._protocol} server does not support stop()")
            return

        try:
            stop()
            if self._server_thread is not None and self._server_thread.is_alive():
                self._server_thread.join(timeout=self._delay + 1)
        finally:
            self._server = None
            self._server_thread = None
