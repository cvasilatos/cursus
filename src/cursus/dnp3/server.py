import importlib
import logging
import time
from dataclasses import dataclass
from types import ModuleType
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from decima.logger import CustomLogger


@dataclass(slots=True)
class Dnp3OutstationConfig:
    """Configuration for the DNP3 outstation emulator."""

    database_size: int = 10
    event_buffer_size: int = 10
    local_addr: int = 10
    remote_addr: int = 1


def _import_pydnp3() -> tuple[ModuleType, ModuleType, ModuleType]:
    try:
        pydnp3_module = importlib.import_module("pydnp3")
    except ModuleNotFoundError as exc:
        msg = "DNP3 support requires 'pydnp3'. Install it with: pip install pydnp3"
        raise RuntimeError(msg) from exc

    return pydnp3_module.asiodnp3, pydnp3_module.asiopal, pydnp3_module.opendnp3


def _create_channel_listener(asiodnp3: ModuleType, logger: "CustomLogger") -> object:
    class ChannelListener(asiodnp3.IChannelListener):
        def __init__(self, log: "CustomLogger") -> None:
            super().__init__()
            self._logger = log

        def OnStateChange(self, state: object) -> None:  # noqa: N802
            self._logger.info(f"DNP3 channel state changed to: {state}")

    return ChannelListener(logger)


def _create_command_handler(opendnp3: ModuleType) -> object:
    class CommandHandler(opendnp3.ICommandHandler):
        def Start(self) -> None:  # noqa: N802
            pass

        def End(self) -> None:  # noqa: N802
            pass

        def Select(self, _command: object, _index: int) -> object:  # noqa: N802
            return opendnp3.CommandStatus.SUCCESS

        def Operate(self, _command: object, _index: int, _op_type: object) -> object:  # noqa: N802
            return opendnp3.CommandStatus.SUCCESS

    return CommandHandler()


class Dnp3Server:
    """DNP3 outstation (emulator) implementation using pydnp3."""

    def __init__(self, ip: str, port: int, config: Dnp3OutstationConfig | None = None) -> None:
        """Initialize the DNP3 outstation server."""
        logger_name = f"{self.__class__.__module__}.{self.__class__.__name__}"
        self.logger: CustomLogger = cast("CustomLogger", logging.getLogger(logger_name))
        self._ip: str = ip
        self._port: int = port
        self._config: Dnp3OutstationConfig = config or Dnp3OutstationConfig()
        self._running: bool = False

        asiodnp3, asiopal, opendnp3 = _import_pydnp3()
        self._asiodnp3 = asiodnp3
        self._opendnp3 = opendnp3

        self._log_handler = asiodnp3.ConsoleLogger().Create()
        self._manager = asiodnp3.DNP3Manager(1, self._log_handler)
        self._retry = asiopal.ChannelRetry().Default()
        self._listener = _create_channel_listener(asiodnp3, self.logger)
        self._channel = self._manager.AddTCPServer(
            "cursus-dnp3-outstation",
            opendnp3.levels.NORMAL | opendnp3.levels.ALL_COMMS,
            self._retry,
            self._ip,
            self._port,
            self._listener,
        )

        self._stack_config = asiodnp3.OutstationStackConfig(
            opendnp3.DatabaseSizes.AllTypes(self._config.database_size),
        )
        self._stack_config.outstation.eventBufferConfig = opendnp3.EventBufferConfig().AllTypes(
            self._config.event_buffer_size,
        )
        self._stack_config.outstation.params.allowUnsolicited = True
        self._stack_config.link.LocalAddr = self._config.local_addr
        self._stack_config.link.RemoteAddr = self._config.remote_addr

        self._command_handler = _create_command_handler(opendnp3)
        self._outstation = self._channel.AddOutstation(
            "cursus-outstation",
            self._command_handler,
            opendnp3.DefaultOutstationApplication.Create(),
            self._stack_config,
        )

    def start(self) -> None:
        """Start the DNP3 outstation and keep it running."""
        if self._running:
            self.logger.warning("DNP3 outstation is already running")
            return

        self.logger.info(f"Starting DNP3 outstation at {self._ip}:{self._port}")
        self._running = True
        self._outstation.Enable()
        try:
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("Stopping DNP3 outstation due to keyboard interrupt")
        finally:
            self.stop()

    def stop(self) -> None:
        """Stop the DNP3 outstation and release resources."""
        if not self._running:
            return

        self._running = False
        self._outstation.Disable()
        self._manager.Shutdown()

    def update_binary_input(self, index: int, *, value: bool) -> None:
        """Update a binary input point in the outstation database."""
        builder = self._asiodnp3.UpdateBuilder()
        builder.Update(self._opendnp3.Binary(value), index)
        self._outstation.Apply(builder.Build())

    def update_analog_input(self, index: int, *, value: float) -> None:
        """Update an analog input point in the outstation database."""
        builder = self._asiodnp3.UpdateBuilder()
        builder.Update(self._opendnp3.Analog(value), index)
        self._outstation.Apply(builder.Build())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    server = Dnp3Server(ip="127.0.0.1", port=20000)
    server.start()
