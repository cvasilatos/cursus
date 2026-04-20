# cursus/dnp3/docker_server.py

import logging
import os
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, cast

from cursus.dnp3.outstation_server import Dnp3OutstationConfig

if TYPE_CHECKING:
    from decima.logger import CustomLogger


class Dnp3DockerServer:
    """DNP3 outstation emulator running in a Docker container."""

    def __init__(self, ip: str, port: int, config: Dnp3OutstationConfig | None = None) -> None:
        """Initialize the DNP3 Docker server."""
        logger_name = f"{self.__class__.__module__}.{self.__class__.__name__}"
        self.logger: CustomLogger = cast("CustomLogger", logging.getLogger(logger_name))
        self._ip = ip
        self._port = port
        self._config = config or Dnp3OutstationConfig()
        self._running = False

    def start(self) -> None:
        """Start the DNP3 Docker service."""
        if self._running:
            self.logger.warning("DNP3 Docker service is already running")
            return

        self.logger.info(f"Starting DNP3 Docker service at {self._ip}:{self._port}")
        self._run_compose("up", "--build", "-d", timeout=60)
        self._running = True

    def stop(self) -> None:
        """Stop the DNP3 Docker service."""
        if not self._running:
            return

        try:
            self._run_compose("down", "--remove-orphans", timeout=20)
        except subprocess.TimeoutExpired:
            self.logger.warning("docker compose down timed out for DNP3, forcing shutdown")
            self._run_compose("kill", timeout=10)
            self._run_compose("down", "--remove-orphans", timeout=20)
        finally:
            self._running = False

    def _run_compose(self, *args: str, timeout: int) -> None:
        subprocess.run(self._compose_command(*args), check=True, env=self._compose_environment(), timeout=timeout)  # noqa: S603

    def _compose_command(self, *args: str) -> list[str]:
        return ["docker", "compose", "-p", self._project_name, "-f", str(self._compose_file), *args]

    def _compose_environment(self) -> dict[str, str]:
        env = os.environ.copy()
        env.update(
            {
                "DNP3_HOST": "0.0.0.0",  # noqa: S104
                "DNP3_PORT": str(self._port),
                "DNP3_DATABASE_SIZE": str(self._config.database_size),
                "DNP3_EVENT_BUFFER_SIZE": str(self._config.event_buffer_size),
                "DNP3_LOCAL_ADDR": str(self._config.local_addr),
                "DNP3_REMOTE_ADDR": str(self._config.remote_addr),
            },
        )
        return env

    @property
    def _compose_file(self) -> Path:
        return Path(__file__).resolve().parent / "assets" / "docker-compose.dnp3.yml"

    @property
    def _project_name(self) -> str:
        return f"cursus-dnp3-{self._port}"
