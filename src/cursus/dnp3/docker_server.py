import logging
import os
import subprocess
import threading
from pathlib import Path
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from decima.logger import CustomLogger


class Dnp3DockerServer:
    """Run the DNP3 outstation inside Docker Compose."""

    def __init__(self, ip: str, port: int) -> None:
        """Initialize the Docker-backed DNP3 runtime."""
        logger_name = f"{self.__class__.__module__}.{self.__class__.__name__}"
        self.logger: CustomLogger = cast("CustomLogger", logging.getLogger(logger_name))
        self._ip = ip
        self._port = port
        self._stop_event = threading.Event()
        self._running = False

    def start(self) -> None:
        """Build and start the DNP3 Docker service, then block until stopped."""
        if self._running:
            self.logger.warning("DNP3 Docker service is already running")
            return

        self._stop_event.clear()
        self.logger.info(f"Starting DNP3 Docker service at {self._ip}:{self._port}")
        self._run_compose("up", "--build", "-d")
        self._running = True

        try:
            self._stop_event.wait()
        finally:
            try:
                self._run_compose("down", "--remove-orphans")
            finally:
                self._running = False

    def stop(self) -> None:
        """Stop the DNP3 Docker service."""
        if not self._running:
            return

        self._stop_event.set()

    def _run_compose(self, *args: str) -> None:
        subprocess.run(  # noqa: S603
            self._compose_command(*args),
            check=True,
            env=self._compose_environment(),
        )

    def _compose_command(self, *args: str) -> list[str]:
        return [
            "docker",
            "compose",
            "-p",
            self._project_name,
            "-f",
            str(self._compose_file),
            *args,
        ]

    def _compose_environment(self) -> dict[str, str]:
        env = os.environ.copy()
        env.update(
            {
                "DNP3_HOST": "0.0.0.0",  # noqa: S104
                "DNP3_PORT": str(self._port),
            },
        )
        return env

    @property
    def _compose_file(self) -> Path:
        return Path(__file__).resolve().parent / "assets" / "docker-compose.dnp3.yml"

    @property
    def _project_name(self) -> str:
        return f"cursus-dnp3-{self._port}"
