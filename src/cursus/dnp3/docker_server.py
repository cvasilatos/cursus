import logging
import os
import subprocess
import tempfile
from importlib import resources
from pathlib import Path
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from decima.logger import CustomLogger

from cursus.dnp3.server import Dnp3OutstationConfig


class Dnp3DockerServer:
    """DNP3 launcher that runs the outstation inside Docker Compose."""

    def __init__(self, ip: str, port: int, config: Dnp3OutstationConfig | None = None) -> None:
        """Initialize the Docker-backed DNP3 launcher."""
        self.logger: CustomLogger = cast("CustomLogger", logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}"))
        self._ip = ip
        self._port = port
        self._config = config or Dnp3OutstationConfig()
        self._process: subprocess.Popen[str] | None = None
        self._workspace: tempfile.TemporaryDirectory[str] | None = None

    def _asset(self, relative_path: str) -> resources.abc.Traversable:
        asset = resources.files("cursus.dnp3").joinpath("assets", *relative_path.split("/"))
        if not asset.is_file():
            msg = f"DNP3 package asset not found: {relative_path}"
            raise FileNotFoundError(msg)
        return asset

    def _build_workspace(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        workspace = tempfile.TemporaryDirectory(prefix="cursus-dnp3-")
        root = Path(workspace.name)

        assets_to_copy = {
            "docker-compose.dnp3.yml": "docker-compose.dnp3.yml",
            "docker/dnp3/Dockerfile": "docker/dnp3/Dockerfile",
            "docker/dnp3/run_server.py": "docker/dnp3/run_server.py",
        }
        for asset_path, destination in assets_to_copy.items():
            target = root / destination
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(self._asset(asset_path).read_bytes())

        package_root = root / "cursus"
        package_root.mkdir(parents=True, exist_ok=True)
        package_files = {
            "__init__.py": resources.files("cursus").joinpath("__init__.py"),
            "dnp3/__init__.py": resources.files("cursus.dnp3").joinpath("__init__.py"),
            "dnp3/server.py": resources.files("cursus.dnp3").joinpath("server.py"),
        }
        for destination, resource_file in package_files.items():
            target = package_root / destination
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(resource_file.read_bytes())

        return workspace, root

    def start(self) -> None:
        """Start the DNP3 server inside Docker Compose and block until it exits."""
        if self._process is not None:
            self.logger.warning("DNP3 Docker server is already running")
            return

        self._workspace, workspace_root = self._build_workspace()
        compose_file = workspace_root / "docker-compose.dnp3.yml"
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
        self._process = subprocess.Popen(command, cwd=workspace_root, env=env, text=True)  # noqa: S603
        try:
            self._process.wait()
        finally:
            self._process = None
            if self._workspace is not None:
                self._workspace.cleanup()
                self._workspace = None

    def stop(self) -> None:
        """Stop the running Docker Compose process."""
        if self._process is None:
            return

        self._process.terminate()
        self._process.wait(timeout=30)
        self._process = None
        if self._workspace is not None:
            self._workspace.cleanup()
            self._workspace = None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    server = Dnp3DockerServer(ip="127.0.0.1", port=20000)
    server.start()
