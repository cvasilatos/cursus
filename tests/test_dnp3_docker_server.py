"""Tests for the Docker-backed DNP3 launcher."""

from pathlib import Path
from unittest.mock import Mock

import pytest

from cursus.dnp3.docker_server import Dnp3DockerServer
from cursus.dnp3.server import Dnp3OutstationConfig


def test_compose_file_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Path, "exists", lambda self: False)
    server = Dnp3DockerServer(ip="127.0.0.1", port=20000)

    with pytest.raises(FileNotFoundError, match="compose file not found"):
        server._compose_file()


def test_start_uses_docker_compose(monkeypatch: pytest.MonkeyPatch) -> None:
    server = Dnp3DockerServer(
        ip="0.0.0.0",
        port=21000,
        config=Dnp3OutstationConfig(
            database_size=12, event_buffer_size=14, local_addr=22, remote_addr=33
        ),
    )
    monkeypatch.setattr(
        server, "_compose_file", lambda: Path("/tmp/docker-compose.dnp3.yml")
    )

    process = Mock()
    popen = Mock(return_value=process)
    monkeypatch.setattr("cursus.dnp3.docker_server.subprocess.Popen", popen)

    server.start()

    command = popen.call_args.args[0]
    env = popen.call_args.kwargs["env"]
    assert command == [
        "docker",
        "compose",
        "-f",
        "/tmp/docker-compose.dnp3.yml",
        "up",
        "--build",
    ]
    assert env["DNP3_HOST"] == "0.0.0.0"
    assert env["DNP3_PORT"] == "21000"
    assert env["DNP3_DATABASE_SIZE"] == "12"
    assert env["DNP3_EVENT_BUFFER_SIZE"] == "14"
    assert env["DNP3_LOCAL_ADDR"] == "22"
    assert env["DNP3_REMOTE_ADDR"] == "33"
    process.wait.assert_called_once()


def test_stop_terminates_running_process() -> None:
    server = Dnp3DockerServer(ip="127.0.0.1", port=20000)
    process = Mock()
    server._process = process

    server.stop()

    process.terminate.assert_called_once()
    process.wait.assert_called_once_with(timeout=30)
    assert server._process is None
