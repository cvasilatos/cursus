import logging
import os

from cursus.dnp3.server import Dnp3OutstationConfig, Dnp3Server


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    return int(value)


def main() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

    server = Dnp3Server(
        ip=os.getenv("DNP3_HOST", "0.0.0.0"),
        port=_env_int("DNP3_PORT", 20000),
        config=Dnp3OutstationConfig(
            database_size=_env_int("DNP3_DATABASE_SIZE", 10),
            event_buffer_size=_env_int("DNP3_EVENT_BUFFER_SIZE", 10),
            local_addr=_env_int("DNP3_LOCAL_ADDR", 10),
            remote_addr=_env_int("DNP3_REMOTE_ADDR", 1),
        ),
    )
    server.start()


if __name__ == "__main__":
    main()
