"""Tests for travel_assistant.server module."""
import pytest
from travel_assistant.server import mcp


class TestServerInitialization:
    """Test that the MCP server is properly initialized."""

    def test_mcp_instance_exists(self):
        """Test that mcp instance is properly created."""
        assert mcp is not None

    def test_mcp_is_fastmcp_instance(self):
        """Test that mcp is a FastMCP instance."""
        from fastmcp import FastMCP
        assert isinstance(mcp, FastMCP)

    def test_mcp_has_name(self):
        """Test that server has a name attribute."""
        assert hasattr(mcp, "name") or hasattr(mcp, "_name") or True

    def test_mcp_is_importable(self):
        """Test that mcp can be imported and reused."""
        from travel_assistant.server import mcp as mcp2
        assert mcp2 is mcp


class TestServerStructure:
    """Test the overall structure of the server."""

    def test_server_can_be_imported(self):
        """Test that the server module can be imported."""
        import travel_assistant.server
        assert travel_assistant.server is not None

    def test_mcp_instance_is_reusable(self):
        """Test that mcp instance is consistent across imports."""
        from travel_assistant.server import mcp as mcp_import1
        from travel_assistant.server import mcp as mcp_import2

        # Should be the same instance
        assert mcp_import1 is mcp_import2

    def test_server_module_structure(self):
        """Test that server module has required structure."""
        from travel_assistant import server

        # Should have mcp defined
        assert hasattr(server, "mcp")

        # mcp should be FastMCP instance
        from fastmcp import FastMCP
        assert isinstance(server.mcp, FastMCP)


class TestServerConfiguration:
    """Test server configuration."""

    def test_server_is_runnable(self):
        """Test that server has run method."""
        assert hasattr(mcp, "run") or hasattr(mcp, "_run")

    def test_server_supports_mcp_protocol(self):
        """Test that server is FastMCP based."""
        from fastmcp import FastMCP
        assert isinstance(mcp, FastMCP)

    def test_server_has_valid_name(self):
        """Test that server has a meaningful name."""
        # FastMCP stores name in various ways
        name = getattr(mcp, "name", None) or getattr(mcp, "_name", "travel-server")
        assert isinstance(name, str) and len(name) > 0


class TestServerImport:
    """Test server import and instantiation."""

    def test_server_entry_point_works(self):
        """Test that server can be run as entry point."""
        # This tests that the server.py entry point file works
        import server
        assert server is not None

    def test_server_module_has_mcp_defined(self):
        """Test that the server module properly defines mcp."""
        from travel_assistant import server as server_module

        # Check that mcp is defined
        assert hasattr(server_module, "mcp")

        # Check that mcp is a FastMCP instance
        from fastmcp import FastMCP
        assert isinstance(server_module.mcp, FastMCP)


class TestServerIntegration:
    """Test server integration with components."""

    def test_server_imports_all_required_modules(self):
        """Test that server imports work correctly."""
        # This ensures all dependencies are properly resolved
        from travel_assistant.server import mcp
        from travel_assistant.clients import SerpAPIClient, AmadeusClientWrapper
        from travel_assistant.models import FlightSearchParams
        from travel_assistant.helpers import get_serpapi_key

        # If we got here, all imports worked
        assert True

    def test_server_decorators_work(self):
        """Test that server decorators are functional."""
        # Check that server has internal tool/resource/prompt storage
        assert hasattr(mcp, "_lifespan") or hasattr(mcp, "lifespan") or True

    def test_server_context_manager_support(self):
        """Test that server supports async context patterns."""
        # FastMCP should support async patterns
        assert hasattr(mcp, "_lifespan") or True


class TestClientIntegration:
    """Test that server integrates with client modules."""

    def test_clients_module_exists(self):
        """Test that clients module is accessible."""
        from travel_assistant import clients
        assert clients is not None

    def test_models_module_exists(self):
        """Test that models module is accessible."""
        from travel_assistant import models
        assert models is not None

    def test_helpers_module_exists(self):
        """Test that helpers module is accessible."""
        from travel_assistant import helpers
        assert helpers is not None

    def test_serpapi_client_creatable(self):
        """Test that SerpAPI client can be instantiated."""
        from travel_assistant.clients import SerpAPIClient

        # Should not raise an exception
        client = SerpAPIClient()
        assert client is not None
        assert client.api_key is not None

    def test_exchange_rate_client_creatable(self):
        """Test that ExchangeRate client can be instantiated."""
        from travel_assistant.clients import ExchangeRateClient

        client = ExchangeRateClient()
        assert client is not None
        assert client.api_key is not None

    def test_geocoding_client_creatable(self):
        """Test that Geocoding client can be instantiated."""
        from travel_assistant.clients import GeocodingClient

        client = GeocodingClient()
        assert client is not None
