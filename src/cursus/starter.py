import importlib
import logging
import socket
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
        self._server_error: BaseException | None = None

        self._ready_event = threading.Event()
        self._ready_monitor_thread: threading.Thread | None = None

    @property
    def ready_event(self) -> threading.Event:
        """Event set when the server endpoint is ready to accept connections."""
        return self._ready_event

    def start_server(self) -> threading.Thread:
        """Start the specified protocol server after a delay.

        Dynamically imports the server module based on the protocol name,
        creates a server instance, and starts it in a daemon thread. A second
        daemon thread probes the configured endpoint and sets `ready_event`
        once the server is reachable. After starting the server, this method
        still waits for the configured delay period for backwards compatibility.

        """
        protocol = self._protocol.lower()
        module_name, class_name = f"cursus.{protocol}.server", f"{protocol.capitalize()}Server"
        module: ModuleType = importlib.import_module(module_name)
        server_class = getattr(module, class_name)
        self._server = server_class(ip="127.0.0.1", port=self._port)

        self._ready_event.clear()

        self._server_error = None
        server_thread = threading.Thread(target=self._run_server, name=class_name, daemon=True)
        self._server_thread = server_thread
        server_thread.start()
        self._start_ready_monitor(class_name)
        self.logger.info(f"[+] Started {self._protocol} server on port {self._port}")
        time.sleep(self._delay)
        if self._server_error is not None:
            raise RuntimeError(f"Failed to start {self._protocol} server on port {self._port}") from self._server_error
        return server_thread

    def wait_until_ready(self, timeout: float | None = None) -> bool:
        """Block until the server endpoint is ready or the timeout elapses."""
        is_ready = self._ready_event.wait(timeout=timeout)
        if not is_ready and self._server_error is not None:
            raise RuntimeError(f"{self._protocol} server failed before becoming ready") from self._server_error

        return is_ready

    def stop_server(self) -> None:
        """Stop the server if it is running and clean up threads."""
        stop = getattr(self._server, "stop", None)
        if stop is None:
            self.logger.warning(f"{self._protocol} server does not support stop()")
            return

        try:
            stop()
            if self._server_thread is not None and self._server_thread.is_alive():
                self._server_thread.join(timeout=self._delay + 1)
                if self._server_thread.is_alive():
                    self.logger.warning(f"{self._protocol} server thread did not exit cleanly")
        finally:
            self._ready_event.clear()
            self._server = None
            self._server_thread = None
            self._ready_monitor_thread = None
            self._server_error = None

    def _run_server(self) -> None:
        """Run the backing server and capture startup failures from the thread."""
        if self._server is None:
            self._server_error = RuntimeError("Server thread started without a backing server instance")
            return

        try:
            self._server.start()
        except BaseException as exc:  # pragma: no cover - re-raised by starter API
            self._server_error = exc
            self.logger.exception(f"{self._protocol} server crashed during startup")

    def _start_ready_monitor(self, class_name: str) -> None:
        """Start a background probe that marks the server as ready."""
        ready_monitor = threading.Thread(target=self._monitor_server_readiness, name=f"{class_name}ReadyMonitor", daemon=True)
        self._ready_monitor_thread = ready_monitor
        ready_monitor.start()

    def _monitor_server_readiness(self) -> None:
        """Poll the server endpoint until it becomes reachable."""
        while self._server_thread is not None and self._server_thread.is_alive():
            if self._server_error is not None:
                return

            if self._is_server_ready():
                if not self._ready_event.is_set():
                    self.logger.info(f"[+] {self._protocol} server is ready on port {self._port}")
                    self._ready_event.set()
                return

            time.sleep(0.1)

    def _is_server_ready(self) -> bool:
        """Return whether the server endpoint is reachable over TCP."""
        try:
            with socket.create_connection(("127.0.0.1", self._port), timeout=0.1):
                return True
        except OSError:
            return False
