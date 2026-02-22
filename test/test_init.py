"""Tests for the top-level cursusd package imports."""

import cursusd
from cursusd import MbtcpServer, S7commServer, Starter, mbtcp, s7comm


class TestPackageImports:
    """Test that main classes are importable from the top-level package."""

    def test_mbtcp_server_importable(self) -> None:
        """Test that MbtcpServer can be imported from the top-level package."""
        assert isinstance(MbtcpServer, type)
        assert MbtcpServer.__name__ == "MbtcpServer"

    def test_s7comm_server_importable(self) -> None:
        """Test that S7commServer can be imported from the top-level package."""
        assert isinstance(S7commServer, type)
        assert S7commServer.__name__ == "S7commServer"

    def test_starter_importable(self) -> None:
        """Test that Starter can be imported from the top-level package."""
        assert isinstance(Starter, type)
        assert Starter.__name__ == "Starter"

    def test_all_exports(self) -> None:
        """Test that __all__ contains the expected public API."""
        assert "MbtcpServer" in cursusd.__all__
        assert "S7commServer" in cursusd.__all__
        assert "Starter" in cursusd.__all__

    def test_mbtcp_subpackage_all(self) -> None:
        """Test that the mbtcp subpackage exports MbtcpServer."""
        assert "MbtcpServer" in mbtcp.__all__

    def test_s7comm_subpackage_all(self) -> None:
        """Test that the s7comm subpackage exports S7commServer."""
        assert "S7commServer" in s7comm.__all__
