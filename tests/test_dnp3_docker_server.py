"""Tests for the Docker-backed DNP3 server."""

from cursus.dnp3.docker_server import Dnp3DockerServer


def test_compose_command_uses_expected_project_and_file() -> None:
    server = Dnp3DockerServer(ip="127.0.0.1", port=20000)

    command = server._compose_command("up", "--build", "-d")

    assert command[:6] == [
        "docker",
        "compose",
        "-p",
        "cursus-dnp3-20000",
        "-f",
        str(server._compose_file),
    ]
    assert command[6:] == ["up", "--build", "-d"]
    assert str(server._compose_file).endswith(
        "src/cursus/dnp3/assets/docker-compose.dnp3.yml"
    )


def test_compose_environment_sets_runtime_binding() -> None:
    server = Dnp3DockerServer(ip="127.0.0.1", port=21000)

    env = server._compose_environment()

    assert env["DNP3_HOST"] == "0.0.0.0"
    assert env["DNP3_PORT"] == "21000"


def test_start_runs_compose_up_and_down(monkeypatch) -> None:
    calls: list[tuple[list[str], dict[str, str]]] = []

    def _fake_run(command: list[str], check: bool, env: dict[str, str]) -> None:
        assert check is True
        calls.append((command, env))

    server = Dnp3DockerServer(ip="127.0.0.1", port=20000)
    monkeypatch.setattr("cursus.dnp3.docker_server.subprocess.run", _fake_run)
    monkeypatch.setattr(server._stop_event, "wait", lambda timeout=None: True)

    server.start()

    assert calls[0][0][-3:] == ["up", "--build", "-d"]
    assert calls[1][0][-2:] == ["down", "--remove-orphans"]
    assert server._running is False


def test_stop_sets_stop_event_when_running() -> None:
    server = Dnp3DockerServer(ip="127.0.0.1", port=20000)
    server._running = True

    server.stop()

    assert server._stop_event.is_set() is True
