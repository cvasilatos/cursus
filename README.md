# Cursus Daemon

The server for ICS protocols (Modbus TCP and S7comm).

## Installation

```bash
# Install dependencies
pip install -e .

# Install with test dependencies
pip install -e ".[test]"
```

## Running Tests

```bash
# Run all tests
pytest test/

# Run tests with coverage report
pytest test/ --cov=cursusd --cov-report=term-missing

# Run tests with verbose output
pytest test/ -v
```

## Test Coverage

The project has comprehensive test coverage:
- 23 tests covering all main modules
- 93% code coverage
- Tests for Starter, MbtcpServer, and S7commServer classes