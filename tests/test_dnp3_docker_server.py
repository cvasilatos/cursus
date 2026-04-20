"""Tests for the Docker-backed DNP3 launcher."""

from pathlib import Path
from unittest.mock import Mock, patch

from cursus.dnp3.docker_server import Dnp3DockerServer
from cursus.dnp3.server import Dnp3OutstationConfig


def test_build_workspace_materializes_packaged_assets() -> None:
    server = Dnp3DockerServer(ip="127.0.0.1", port=20000)

    workspace, root = server._build_workspace()
    try:
        assert (root / "docker-compose.dnp3.yml").is_file()
        assert (root / "docker/dnp3/Dockerfile").is_file()
        assert (root / "docker/dnp3/run_server.py").is_file()
        assert (root / "cursus/__init__.py").is_file()
        assert (root / "cursus/dnp3/server.py").is_file()
    finally:
        workspace.cleanup()


def test_start_uses_docker_compose(monkeypatch) -> None:
    server = Dnp3DockerServer(
        ip="0.0.0.0",
        port=21000,
        config=Dnp3OutstationConfig(
            database_size=12, event_buffer_size=14, local_addr=22, remote_addr=33
        ),
    )

    process = Mock()

    def wait() -> None:
        workspace = popen.call_args.kwargs["cwd"]
        assert workspace.joinpath("docker-compose.dnp3.yml").is_file()
        assert workspace.joinpath("docker/dnp3/Dockerfile").is_file()
        assert workspace.joinpath("cursus/dnp3/server.py").is_file()

    process.wait.side_effect = wait
    popen = Mock(return_value=process)
    run = Mock()
    monkeypatch.setattr("cursus.dnp3.docker_server.subprocess.Popen", popen)
    monkeypatch.setattr("cursus.dnp3.docker_server.subprocess.run", run)

    server.start()

    command = popen.call_args.args[0]
    env = popen.call_args.kwargs["env"]
    assert command == [
        "docker",
        "compose",
        "-f",
        str(popen.call_args.kwargs["cwd"] / "docker-compose.dnp3.yml"),
        "up",
        "--build",
    ]
    assert popen.call_args.kwargs["cwd"].name.startswith("cursus-dnp3-")
    assert env["DNP3_HOST"] == "0.0.0.0"
    assert env["DNP3_PORT"] == "21000"
    assert env["DNP3_DATABASE_SIZE"] == "12"
    assert env["DNP3_EVENT_BUFFER_SIZE"] == "14"
    assert env["DNP3_LOCAL_ADDR"] == "22"
    assert env["DNP3_REMOTE_ADDR"] == "33"
    process.wait.assert_called_once()
    run.assert_called_once_with(
        [
            "docker",
            "compose",
            "-f",
            str(popen.call_args.kwargs["cwd"] / "docker-compose.dnp3.yml"),
            "down",
            "--remove-orphans",
        ],
        cwd=popen.call_args.kwargs["cwd"],
        check=False,
        text=True,
    )
    assert server._workspace is None
    assert server._workspace_root is None
    assert server._compose_file is None


def test_stop_terminates_running_process() -> None:
    server = Dnp3DockerServer(ip="127.0.0.1", port=20000)
    process = Mock()
    workspace = Mock()
    workspace_root = Path("/tmp/cursus-dnp3-test")
    compose_file = workspace_root / "docker-compose.dnp3.yml"
    run = Mock()
    server._process = process
    server._workspace = workspace
    server._workspace_root = workspace_root
    server._compose_file = compose_file

    with patch("cursus.dnp3.docker_server.subprocess.run", run):
        server.stop()

    process.terminate.assert_called_once()
    process.wait.assert_called_once_with(timeout=30)
    run.assert_called_once_with(
        [
            "docker",
            "compose",
            "-f",
            str(compose_file),
            "down",
            "--remove-orphans",
        ],
        cwd=workspace_root,
        check=False,
        text=True,
    )
    workspace.cleanup.assert_called_once()
    assert server._process is None
    assert server._workspace is None
    assert server._workspace_root is None
    assert server._compose_file is None
