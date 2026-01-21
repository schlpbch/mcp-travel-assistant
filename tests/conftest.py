"""Shared pytest fixtures for travel_assistant tests."""

from unittest.mock import Mock

import pytest


@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """Automatically set environment variables for all tests."""
    monkeypatch.setenv("SERPAPI_KEY", "test-serpapi-key-12345")
    monkeypatch.setenv("AMADEUS_API_KEY", "test-amadeus-key-12345")
    monkeypatch.setenv("AMADEUS_API_SECRET", "test-amadeus-secret-12345")
    monkeypatch.setenv("EXCHANGE_RATE_API_KEY", "test-exchange-key-12345")


@pytest.fixture
def mock_amadeus_client():
    """Create a mock Amadeus client for testing."""
    client = Mock()
    # Add mock methods for shopping endpoints
    client.shopping = Mock()
    client.shopping.flight_offers_search = Mock()
    client.shopping.hotel_search_api = Mock()
    client.shopping.activities = Mock()
    return client


@pytest.fixture
def mock_responses_wrapper(monkeypatch):
    """Provide a mock responses context for easier HTTP mocking."""
    import responses

    @pytest.fixture
    def _mock_responses():
        with responses.RequestsMock() as rsps:
            yield rsps

    return _mock_responses
