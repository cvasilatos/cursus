# CursusD (Cursus Daemon)

A Python server daemon for Industrial Control System (ICS) protocols. CursusD provides implementations for **Modbus TCP** and **S7comm** protocols, enabling simulation of industrial controllers for testing, development, security research, and training environments.

## Features

- **Modbus TCP Server**: Full-featured Modbus TCP server implementation using pymodbus
  - Supports all standard Modbus data tables (Coils, Discrete Inputs, Holding Registers, Input Registers)
  - Configurable data block sizes (default: 32000 registers)
  - Emulates WAGO PFC200 device identity

- **S7comm Server**: Siemens S7 protocol server implementation using python-snap7
  - Supports multiple S7 data areas (DB, PA, PE, MK, TM, CT)
  - Configurable memory sizes
  - Compatible with standard S7 clients

- **Starter Class**: Convenient server management
  - Dynamic protocol server initialization
  - Thread-based server execution
  - Configurable startup delays

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

# Install with test dependencies
uv sync --extra test
```

Alternatively, using pip:

```bash
# Install dependencies
pip install -e .

# Install with test dependencies
pip install -e ".[test]"
```

## Usage

### Running Servers Directly

#### Modbus TCP Server

```python
from cursus.mbtcp.server import MbtcpServer

# Create and start a Modbus TCP server
server = MbtcpServer(ip="127.0.0.1", port=502, size=32000)
server.start()  # Blocks and runs the server
```

Or run directly from command line:

```bash
python -m cursus.mbtcp.server
```

#### S7comm Server

```python
from cursus.s7comm.server import S7commServer

# Create and start an S7comm server
server = S7commServer(ip="127.0.0.1", port=102, size=32000)
server.start()  # Blocks and runs the server
```

Or run directly from command line:

```bash
python -m cursus.s7comm.server
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
```

## Development

### Running Tests

```bash
# Run all tests using uv
uv run pytest test/

# Run tests with coverage report
uv run pytest test/ --cov=cursus --cov-report=term-missing

# Run tests with verbose output
uv run pytest test/ -v
```

Alternatively, using pytest directly:

```bash
# Run all tests
pytest test/

# Run tests with coverage report
pytest test/ --cov=cursus --cov-report=term-missing

# Run tests with verbose output
pytest test/ -v
```

### Test Coverage

The project has comprehensive test coverage:
- 23 tests covering all main modules
- 93% code coverage
- Tests for Starter, MbtcpServer, and S7commServer classes

### Code Quality

This project uses ruff for linting and formatting:

```bash
# Run linter
uv run ruff check .

# Format code
uv run ruff format .
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
S7commServer(ip: str, port: int, size: int = 32000)
```

**Parameters:**

- `ip`: IP address to bind the server to
- `port`: TCP port number (default S7 port is 102)
- `size`: Size of memory areas in bytes (default: 32000)

### Starter

```python
Starter(protocol: str, port: int, delay: int)
```

**Parameters:**

- `protocol`: Protocol name ("mbtcp" or "s7comm")
- `port`: Port number for the server
- `delay`: Delay in seconds after starting the server

## License

This project is open source. Please refer to the LICENSE file for more information.

## Requirements

- Python >= 3.12
- pymodbus >= 3.12.0
- python-snap7 >= 1.3, < 3.0
- decima (custom logging library)
