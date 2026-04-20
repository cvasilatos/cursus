import logging
from typing import TYPE_CHECKING, Literal, cast

from cursus.dnp3.docker_server import Dnp3DockerServer
from cursus.dnp3.outstation_server import Dnp3OutstationConfig, Dnp3OutstationServer

if TYPE_CHECKING:
    from decima.logger import CustomLogger


class Dnp3Server:
    """Public DNP3 server entry point following the standard protocol naming."""

    def __init__(
        self,
        ip: str,
        port: int,
        config: Dnp3OutstationConfig | None = None,
        runtime: Literal["docker", "native"] = "docker",
    ) -> None:
        """Initialize the DNP3 server.

        Args:
            ip: The IP address to bind the server to.
            port: The TCP port number to listen on.
            config: DNP3 outstation configuration values.
            runtime: Runtime backend. Use `"docker"` for the bundled container
                or `"native"` for a direct `pydnp3` outstation.

        """
        logger_name = f"{self.__class__.__module__}.{self.__class__.__name__}"
        self.logger: CustomLogger = cast("CustomLogger", logging.getLogger(logger_name))
        self._ip = ip
        self._port = port
        self._config = config or Dnp3OutstationConfig()
        self._runtime = runtime
        self._server = self._create_server()

    def _create_server(self) -> Dnp3DockerServer | Dnp3OutstationServer:
        if self._runtime == "docker":
            return Dnp3DockerServer(ip=self._ip, port=self._port, config=self._config)
        if self._runtime == "native":
            return Dnp3OutstationServer(ip=self._ip, port=self._port, config=self._config)

        raise ValueError(f"Unsupported DNP3 runtime: {self._runtime}")

    def start(self) -> None:
        """Start the configured DNP3 runtime."""
        self._server.start()

    def stop(self) -> None:
        """Stop the configured DNP3 runtime when supported."""
        stop = getattr(self._server, "stop", None)
        if stop is not None:
            stop()

    def update_binary_input(self, index: int, *, value: bool) -> None:
        """Update a binary point when using the native outstation runtime."""
        if not isinstance(self._server, Dnp3OutstationServer):
            raise TypeError("Binary point updates require runtime='native'")

        self._server.update_binary_input(index=index, value=value)

    def update_analog_input(self, index: int, *, value: float) -> None:
        """Update an analog point when using the native outstation runtime."""
        if not isinstance(self._server, Dnp3OutstationServer):
            raise TypeError("Analog point updates require runtime='native'")

        self._server.update_analog_input(index=index, value=value)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    server = Dnp3OutstationServer(ip="127.0.0.1", port=20000)
    server.start()
