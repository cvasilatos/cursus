"""Configuration for pytest tests."""

import sys
from unittest.mock import MagicMock

# Mock the decimalog module since it's a git dependency
sys.modules["decimalog"] = MagicMock()
sys.modules["decimalog.logger"] = MagicMock()
