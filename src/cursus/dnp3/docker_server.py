import logging
import os
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from decima.logger import CustomLogger

from cursus.dnp3.server import Dnp3OutstationConfig


class Dnp3DockerServer:
    """DNP3 launcher that runs the outstation inside Docker Compose."""

    def __init__(self, ip: str, port: int, config: Dnp3OutstationConfig | None = None) -> None:
        self.logger: CustomLogger = cast("CustomLogger", logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}"))
        self._ip = ip
        self._port = port
        self._config = config or Dnp3OutstationConfig()
        self._process: subprocess.Popen[str] | None = None

    def _compose_file(self) -> Path:
        compose_file = Path(__file__).resolve().parents[3] / "docker-compose.dnp3.yml"
        if not compose_file.exists():
            msg = f"DNP3 Docker compose file not found: {compose_file}"
            raise FileNotFoundError(msg)
        return compose_file

    def start(self) -> None:
        """Start the DNP3 server inside Docker Compose and block until it exits."""
        if self._process is not None:
            self.logger.warning("DNP3 Docker server is already running")
            return

        compose_file = self._compose_file()
        env = os.environ.copy()
        env.update(
            {
                "DNP3_HOST": self._ip,
                "DNP3_PORT": str(self._port),
                "DNP3_LOCAL_ADDR": str(self._config.local_addr),
                "DNP3_REMOTE_ADDR": str(self._config.remote_addr),
                "DNP3_DATABASE_SIZE": str(self._config.database_size),
                "DNP3_EVENT_BUFFER_SIZE": str(self._config.event_buffer_size),
            },
        )

        command = ["docker", "compose", "-f", str(compose_file), "up", "--build"]
        self.logger.info(f"Starting DNP3 Docker server at {self._ip}:{self._port}")
        self._process = subprocess.Popen(command, env=env, text=True)
        try:
            self._process.wait()
        finally:
            self._process = None

    def stop(self) -> None:
        """Stop the running Docker Compose process."""
        if self._process is None:
            return

        self._process.terminate()
        self._process.wait(timeout=30)
        self._process = None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    server = Dnp3DockerServer(ip="127.0.0.1", port=20000)
    server.start()
