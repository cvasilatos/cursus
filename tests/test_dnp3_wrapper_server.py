"""Tests for the public DNP3 server wrapper."""

import pytest

from cursus.dnp3.outstation_server import Dnp3OutstationConfig
from cursus.dnp3.server import Dnp3Server


def test_initialization_uses_docker_runtime_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created = []

    class _FakeDockerServer:
        def __init__(
            self, ip: str, port: int, config: Dnp3OutstationConfig | None = None
        ) -> None:
            created.append((ip, port, config))

        def start(self) -> None:
            pass

        def stop(self) -> None:
            pass

    monkeypatch.setattr("cursus.dnp3.server.Dnp3DockerServer", _FakeDockerServer)

    config = Dnp3OutstationConfig(database_size=32)
    server = Dnp3Server(ip="127.0.0.1", port=20000, config=config)

    assert created == [("127.0.0.1", 20000, config)]
    assert server._runtime == "docker"


def test_initialization_uses_native_runtime_when_requested(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created = []

    class _FakeOutstationServer:
        def __init__(
            self, ip: str, port: int, config: Dnp3OutstationConfig | None = None
        ) -> None:
            created.append((ip, port, config))

        def start(self) -> None:
            pass

        def stop(self) -> None:
            pass

    monkeypatch.setattr(
        "cursus.dnp3.server.Dnp3OutstationServer", _FakeOutstationServer
    )

    config = Dnp3OutstationConfig(database_size=32)
    server = Dnp3Server(ip="127.0.0.1", port=20000, config=config, runtime="native")

    assert created == [("127.0.0.1", 20000, config)]
    assert server._runtime == "native"


def test_binary_updates_require_native_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeDockerServer:
        def __init__(
            self, ip: str, port: int, config: Dnp3OutstationConfig | None = None
        ) -> None:
            del ip, port, config

        def start(self) -> None:
            pass

        def stop(self) -> None:
            pass

    monkeypatch.setattr("cursus.dnp3.server.Dnp3DockerServer", _FakeDockerServer)

    server = Dnp3Server(ip="127.0.0.1", port=20000)

    with pytest.raises(TypeError, match="runtime='native'"):
        server.update_binary_input(index=1, value=True)
