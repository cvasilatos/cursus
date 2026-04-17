"""Tests for the DNP3 server."""

from types import SimpleNamespace

import pytest
from cursus.dnp3.server import Dnp3OutstationConfig, Dnp3Server


class _FakeConsoleLogger:
    def Create(self):  # noqa: N802
        return object()


class _FakeRetry:
    def Default(self):  # noqa: N802
        return "retry-default"


class _FakeUpdateBuilder:
    def __init__(self):
        self._updates = []

    def Update(self, point, index):  # noqa: N802
        self._updates.append((point, index))

    def Build(self):  # noqa: N802
        return tuple(self._updates)


class _FakeOutstation:
    def __init__(self):
        self.enabled = False
        self.disabled = False
        self.applied = []

    def Enable(self):  # noqa: N802
        self.enabled = True

    def Disable(self):  # noqa: N802
        self.disabled = True

    def Apply(self, update):  # noqa: N802
        self.applied.append(update)


class _FakeChannel:
    def __init__(self):
        self.outstation = _FakeOutstation()
        self.add_outstation_args = None

    def AddOutstation(self, *args):  # noqa: N802
        self.add_outstation_args = args
        return self.outstation


class _FakeManager:
    def __init__(self, threads, log_handler):
        self.threads = threads
        self.log_handler = log_handler
        self.channel = _FakeChannel()
        self.shutdown_called = False
        self.server_args = None

    def AddTCPServer(self, *args):  # noqa: N802
        self.server_args = args
        return self.channel

    def Shutdown(self):  # noqa: N802
        self.shutdown_called = True


class _FakeDefaultOutstationApplication:
    @staticmethod
    def Create():  # noqa: N802
        return "default-outstation-app"


def _build_fake_modules():
    managers = []

    def manager_factory(threads, log_handler):
        manager = _FakeManager(threads, log_handler)
        managers.append(manager)
        return manager

    outstation = SimpleNamespace(
        eventBufferConfig=None,
        params=SimpleNamespace(allowUnsolicited=False),
    )
    link = SimpleNamespace(LocalAddr=0, RemoteAddr=0)
    config = SimpleNamespace(outstation=outstation, link=link)

    asiodnp3 = SimpleNamespace(
        IChannelListener=type("IChannelListener", (), {"__init__": lambda self: None}),
        ConsoleLogger=_FakeConsoleLogger,
        DNP3Manager=manager_factory,
        OutstationStackConfig=lambda _db: config,
        UpdateBuilder=_FakeUpdateBuilder,
    )
    asiopal = SimpleNamespace(ChannelRetry=_FakeRetry)
    opendnp3 = SimpleNamespace(
        ICommandHandler=type("ICommandHandler", (), {}),
        CommandStatus=SimpleNamespace(SUCCESS="SUCCESS"),
        DatabaseSizes=SimpleNamespace(AllTypes=lambda size: f"db-{size}"),
        EventBufferConfig=lambda: SimpleNamespace(
            AllTypes=lambda size: f"event-{size}",
        ),
        levels=SimpleNamespace(NORMAL=1, ALL_COMMS=2),
        DefaultOutstationApplication=_FakeDefaultOutstationApplication,
        Binary=lambda value: ("Binary", value),
        Analog=lambda value: ("Analog", value),
    )

    return asiodnp3, asiopal, opendnp3, managers, config


def test_initialization(monkeypatch: pytest.MonkeyPatch) -> None:
    asiodnp3, asiopal, opendnp3, managers, config = _build_fake_modules()
    monkeypatch.setattr(
        "cursus.dnp3.server._import_pydnp3",
        lambda: (asiodnp3, asiopal, opendnp3),
    )

    server = Dnp3Server(ip="127.0.0.1", port=20000, config=Dnp3OutstationConfig())

    assert server._ip == "127.0.0.1"
    assert server._port == 20000
    assert config.outstation.eventBufferConfig == "event-10"
    assert config.outstation.params.allowUnsolicited is True
    assert config.link.LocalAddr == 10
    assert config.link.RemoteAddr == 1
    assert managers[0].server_args[3] == "127.0.0.1"
    assert managers[0].server_args[4] == 20000


def test_start_and_stop(monkeypatch: pytest.MonkeyPatch) -> None:
    asiodnp3, asiopal, opendnp3, managers, _config = _build_fake_modules()
    monkeypatch.setattr(
        "cursus.dnp3.server._import_pydnp3",
        lambda: (asiodnp3, asiopal, opendnp3),
    )

    def _raise_keyboard_interrupt(_seconds: int) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr("cursus.dnp3.server.time.sleep", _raise_keyboard_interrupt)

    server = Dnp3Server(ip="127.0.0.1", port=20000, config=Dnp3OutstationConfig())
    manager = managers[0]
    outstation = manager.channel.outstation

    server.start()

    assert outstation.enabled is True
    assert outstation.disabled is True
    assert manager.shutdown_called is True


def test_point_updates(monkeypatch: pytest.MonkeyPatch) -> None:
    asiodnp3, asiopal, opendnp3, managers, _config = _build_fake_modules()
    monkeypatch.setattr(
        "cursus.dnp3.server._import_pydnp3",
        lambda: (asiodnp3, asiopal, opendnp3),
    )

    server = Dnp3Server(ip="127.0.0.1", port=20000, config=Dnp3OutstationConfig())
    outstation = managers[0].channel.outstation

    server.update_binary_input(index=3, value=True)
    server.update_analog_input(index=5, value=12.5)

    assert outstation.applied[0] == ((("Binary", True), 3),)
    assert outstation.applied[1] == ((("Analog", 12.5), 5),)
