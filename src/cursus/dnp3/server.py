import logging
import time
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from decima.logger import CustomLogger


def _import_pydnp3() -> tuple[Any, Any, Any]:
    try:
        from pydnp3 import asiodnp3, asiopal, opendnp3
    except ModuleNotFoundError as exc:
        msg = "DNP3 support requires 'pydnp3'. Install it with: pip install pydnp3"
        raise RuntimeError(msg) from exc

    return asiodnp3, asiopal, opendnp3


class _ChannelListener:
    def __init__(self, asiodnp3: Any, logger: Any) -> None:
        class Listener(asiodnp3.IChannelListener):
            def __init__(self, log: Any) -> None:
                super().__init__()
                self._logger = log

            def OnStateChange(self, state: Any) -> None:  # noqa: N802
                self._logger.info(f"DNP3 channel state changed to: {state}")

        self.listener = Listener(logger)


class _CommandHandler:
    def __init__(self, opendnp3: Any) -> None:
        class Handler(opendnp3.ICommandHandler):
            def Start(self) -> None:  # noqa: N802
                return

            def End(self) -> None:  # noqa: N802
                return

            def Select(self, command: Any, index: int) -> Any:  # noqa: N802
                return opendnp3.CommandStatus.SUCCESS

            def Operate(self, command: Any, index: int, op_type: Any) -> Any:  # noqa: N802
                return opendnp3.CommandStatus.SUCCESS

        self.handler = Handler()


class Dnp3Server:
    """DNP3 outstation (emulator) implementation using pydnp3."""

    def __init__(
        self,
        ip: str,
        port: int,
        database_size: int = 10,
        event_buffer_size: int = 10,
        local_addr: int = 10,
        remote_addr: int = 1,
    ) -> None:
        self.logger: CustomLogger = cast("CustomLogger", logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}"))
        self._ip: str = ip
        self._port: int = port
        self._database_size: int = database_size
        self._event_buffer_size: int = event_buffer_size
        self._local_addr: int = local_addr
        self._remote_addr: int = remote_addr
        self._running: bool = False

        asiodnp3, asiopal, opendnp3 = _import_pydnp3()
        self._asiodnp3 = asiodnp3
        self._opendnp3 = opendnp3

        self._log_handler = asiodnp3.ConsoleLogger().Create()
        self._manager = asiodnp3.DNP3Manager(1, self._log_handler)
        self._retry = asiopal.ChannelRetry().Default()
        self._listener = _ChannelListener(asiodnp3, self.logger).listener
        self._channel = self._manager.AddTCPServer(
            "cursus-dnp3-outstation",
            opendnp3.levels.NORMAL | opendnp3.levels.ALL_COMMS,
            self._retry,
            self._ip,
            self._port,
            self._listener,
        )

        self._stack_config = asiodnp3.OutstationStackConfig(opendnp3.DatabaseSizes.AllTypes(database_size))
        self._stack_config.outstation.eventBufferConfig = opendnp3.EventBufferConfig().AllTypes(event_buffer_size)
        self._stack_config.outstation.params.allowUnsolicited = True
        self._stack_config.link.LocalAddr = local_addr
        self._stack_config.link.RemoteAddr = remote_addr

        self._command_handler = _CommandHandler(opendnp3).handler
        self._outstation = self._channel.AddOutstation(
            "cursus-outstation",
            self._command_handler,
            asiodnp3.DefaultOutstationApplication.Instance(),
            self._stack_config,
        )

    def start(self) -> None:
        """Start the DNP3 outstation and keep it running."""
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

    def update_binary_input(self, index: int, value: bool) -> None:
        """Update a binary input point in the outstation database."""
        builder = self._asiodnp3.UpdateBuilder()
        builder.Update(self._opendnp3.Binary(value), index)
        self._outstation.Apply(builder.Build())

    def update_analog_input(self, index: int, value: float) -> None:
        """Update an analog input point in the outstation database."""
        builder = self._asiodnp3.UpdateBuilder()
        builder.Update(self._opendnp3.Analog(value), index)
        self._outstation.Apply(builder.Build())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    server = Dnp3Server(ip="127.0.0.1", port=20000)
    server.start()

