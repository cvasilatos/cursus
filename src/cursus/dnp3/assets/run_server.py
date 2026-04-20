import logging
import os

from cursus.dnp3.outstation_server import Dnp3OutstationConfig, Dnp3OutstationServer


def _read_int(name: str, default: int) -> int:
    return int(os.environ.get(name, default))


def main() -> None:
    """Start the in-container DNP3 server using environment configuration."""
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))

    server = Dnp3OutstationServer(
        ip=os.environ.get("DNP3_HOST", "0.0.0.0"),  # noqa: S104
        port=_read_int("DNP3_PORT", 20000),
        config=Dnp3OutstationConfig(
            database_size=_read_int("DNP3_DATABASE_SIZE", 10),
            event_buffer_size=_read_int("DNP3_EVENT_BUFFER_SIZE", 10),
            local_addr=_read_int("DNP3_LOCAL_ADDR", 10),
            remote_addr=_read_int("DNP3_REMOTE_ADDR", 1),
        ),
    )
    server.start()


if __name__ == "__main__":
    main()
