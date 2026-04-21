# CursusD (Cursus Daemon)

A Python server daemon for Industrial Control System (ICS) protocols. CursusD provides implementations for **Modbus TCP**, **S7comm**, **EtherNet/IP (CIP)**, and **DNP3 outstation** protocols, enabling simulation of industrial controllers for testing, development, security research, and training environments.

## Features

- **Modbus TCP Server**: Full-featured Modbus TCP server implementation using pymodbus
  - Supports all standard Modbus data tables (Coils, Discrete Inputs, Holding Registers, Input Registers)
  - Configurable data block sizes (default: 32000 registers)
  - Emulates WAGO PFC200 device identity

- **S7comm Server**: Siemens S7 protocol server implementation using python-snap7
  - Supports multiple S7 data areas (DB, PA, PE, MK, TM, CT)
  - Configurable memory sizes
  - Compatible with standard S7 clients

- **EtherNet/IP Server**: Pure-Python EtherNet/IP explicit-message emulator
  - Handles EtherNet/IP discovery commands (`ListServices`, `ListIdentity`, `ListInterfaces`)
  - Supports encapsulation session registration and `SendRRData`
  - Exposes CIP Identity and Assembly objects for `Get_Attribute_Single` / `Set_Attribute_Single`
  - Defaults to Allen-Bradley-like identity values for discovery and testing

- **DNP3 Outstation Server**: DNP3 outstation emulator using pydnp3
  - TCP server mode for DNP3 master connectivity
  - Configurable DNP3 addresses and database sizes
  - Binary and analog point update helpers
  - Docker-backed starter flow so the host environment does not need `pydnp3`

- **Starter Class**: Convenient server management
  - Dynamic protocol server initialization
  - Thread-based server execution
  - Configurable startup delays
  - Ready signal emitted when the endpoint becomes reachable

## Installation

This project uses [uv](https://docs.astral.sh/uv/) for dependency management. Install uv first if you don't have it:

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then install the project:

```bash
# Install dependencies
uv sync

# Install with development and test dependencies
uv sync --group dev --group test
```

Alternatively, using pip:

```bash
# Install dependencies
pip install -e .

# Install development and test tools
pip install ruff pytest pytest-cov
```

`Starter(protocol="dnp3", ...)` now follows the same `cursus.<protocol>.server.<Protocol>Server` convention as the other protocols and uses the bundled Docker runtime through `cursus.dnp3.server.Dnp3Server`. The native `pydnp3` outstation remains available as `cursus.dnp3.server.Dnp3OutstationServer`.

## Usage

### Running Servers Directly

#### Modbus TCP Server

```python
from cursus.mbtcp.server import MbtcpServer

# Create and start a Modbus TCP server
server = MbtcpServer(ip="127.0.0.1", port=502, size=32000)
server.start()  # Blocks and runs the server
```

#### S7comm Server

```python
from cursus.s7comm.server import S7commServer

# Create and start an S7comm server
server = S7commServer(ip="127.0.0.1", port=102, size=1024)
server.start()  # Blocks and runs the server
```

Or run directly from command line:

```bash
python -m cursus.s7comm.server
```

#### DNP3 Outstation Server

```python
from cursus.dnp3.server import Dnp3OutstationServer

# Create and start a DNP3 outstation
server = Dnp3OutstationServer(ip="127.0.0.1", port=20000)
server.start()  # Blocks and runs until interrupted
```

Or run directly from command line:

```bash
python -m cursus.dnp3.outstation_server
```

#### EtherNet/IP Server

```python
from cursus.enip.server import EnipServer

# Create and start an EtherNet/IP explicit-message server
server = EnipServer(ip="127.0.0.1", port=44818)
server.start()  # Blocks and runs the server
```

### Using the Starter Class

The Starter class provides a convenient way to initialize and start protocol servers in daemon threads:

```python
from cursus.starter import Starter

# Start a Modbus TCP server
mbtcp_starter = Starter(protocol="mbtcp", port=502, delay=1)
mbtcp_starter.start_server()

# Start an S7comm server
s7comm_starter = Starter(protocol="s7comm", port=102, delay=2)
s7comm_starter.start_server()

# Start an EtherNet/IP server
enip_starter = Starter(protocol="enip", port=44818, delay=1)
enip_starter.start_server()

# Start a DNP3 outstation server
dnp3_starter = Starter(protocol="dnp3", port=20000, delay=2)
dnp3_starter.start_server()
dnp3_starter.wait_until_ready(timeout=30)
dnp3_starter.stop_server()
```

`Starter.ready_event` is set when the server endpoint is reachable over TCP. This provides a protocol-neutral readiness signal for projects using Cursus, including `dnp3` when it is started through Docker and needs extra time before accepting connections.

For `dnp3`, Docker and the Docker Compose plugin must be installed on the machine running the starter.

## Development

### Running Tests

```bash
# Run all tests using uv
uv run pytest tests/

# Run tests with coverage report
uv run pytest tests/ --cov=cursus --cov-report=term-missing

# Run tests with verbose output
uv run pytest tests/ -v
```

Alternatively, using pytest directly:

```bash
# Run all tests
python -m pytest tests/

# Run tests with coverage report
python -m pytest tests/ --cov=cursus --cov-report=term-missing

# Run tests with verbose output
python -m pytest tests/ -v
```

### Code Quality

This project uses ruff for linting and formatting:

```bash
# Run linter
python -m ruff check .

# Format code
python -m ruff format .
```

## API Reference

### MbtcpServer

```python
MbtcpServer(ip: str, port: int, size: int = 32000)
```

**Parameters:**

- `ip`: IP address to bind the server to
- `port`: TCP port number (default Modbus port is 502)
- `size`: Size of data blocks in registers (default: 32000)

### S7commServer

```python
S7commServer(ip: str, port: int, size: int = 1024)
```

**Parameters:**

- `ip`: IP address to bind the server to
- `port`: TCP port number (default S7 port is 102)
- `size`: Size of memory areas in bytes (default: 1024)

### EnipServer

```python
EnipServer(ip: str, port: int = 44818, config: EnipServerConfig | None = None)
```

**Parameters:**

- `ip`: IP address to bind the server to
- `port`: TCP port number (default EtherNet/IP explicit-messaging port is 44818)
- `config`: Optional identity and assembly configuration for the emulator

### Starter

```python
Starter(protocol: str, port: int, delay: int)
```

**Parameters:**

- `protocol`: Protocol name ("mbtcp", "s7comm", "enip", or "dnp3")
- `port`: Port number for the server
- `delay`: Delay in seconds after starting the server

**Readiness:**

- `ready_event`: `threading.Event` set once the server endpoint accepts TCP connections
- `wait_until_ready(timeout: float | None = None) -> bool`: wait for the ready signal

## License

This project is open source. Please refer to the LICENSE file for more information.

## Requirements

- Python >= 3.12
- pymodbus >= 3.12.0
- python-snap7 >= 1.3, < 3.0
- decima (custom logging library)
