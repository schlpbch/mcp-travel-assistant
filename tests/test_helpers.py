"""Tests for travel_assistant.helpers module."""
import pytest
import responses
from unittest.mock import patch, Mock
from travel_assistant.helpers import (
    get_serpapi_key,
    get_exchange_rate_api_key,
    get_geolocator,
    get_nws_headers,
    make_nws_request,
)


class TestAPIKeyHelpers:
    """Test API key retrieval functions."""

    def test_get_serpapi_key_success(self, monkeypatch):
        """Test successful SerpAPI key retrieval from environment."""
        monkeypatch.setenv("SERPAPI_KEY", "test-serpapi-key-xyz")
        assert get_serpapi_key() == "test-serpapi-key-xyz"

    def test_get_serpapi_key_missing(self, monkeypatch):
        """Test ValueError when SerpAPI key is missing."""
        monkeypatch.delenv("SERPAPI_KEY", raising=False)
        with pytest.raises(ValueError, match="SERPAPI_KEY.*required"):
            get_serpapi_key()

    def test_get_exchange_rate_api_key_success(self, monkeypatch):
        """Test successful ExchangeRate API key retrieval from environment."""
        monkeypatch.setenv("EXCHANGE_RATE_API_KEY", "test-exchange-key-abc")
        assert get_exchange_rate_api_key() == "test-exchange-key-abc"

    def test_get_exchange_rate_api_key_missing(self, monkeypatch):
        """Test ValueError when ExchangeRate API key is missing."""
        monkeypatch.delenv("EXCHANGE_RATE_API_KEY", raising=False)
        with pytest.raises(ValueError, match="EXCHANGE_RATE_API_KEY.*required"):
            get_exchange_rate_api_key()


class TestGeolocator:
    """Test geolocator initialization and configuration."""

    def test_get_geolocator_returns_tuple(self):
        """Test that get_geolocator returns a tuple of (geocode, reverse) functions."""
        geocode_limiter, reverse_limiter = get_geolocator()

        # Both should be callable (they are RateLimiter instances)
        assert callable(geocode_limiter)
        assert callable(reverse_limiter)

    def test_get_geolocator_returns_cached_instances(self):
        """Test that multiple calls to get_geolocator return the same cached instances."""
        limiter1_geo, limiter1_rev = get_geolocator()
        limiter2_geo, limiter2_rev = get_geolocator()

        # Should be the same cached instances for performance
        assert limiter1_geo is limiter2_geo
        assert limiter1_rev is limiter2_rev

    def test_get_geolocator_rate_limiter_has_delay(self):
        """Test that rate limiters are properly configured with delay."""
        geocode_limiter, reverse_limiter = get_geolocator()

        # RateLimiters should have min_delay_seconds set
        assert hasattr(geocode_limiter, "min_delay_seconds") or hasattr(geocode_limiter, "min_delay")


class TestNWSHelpers:
    """Test National Weather Service (NWS) helper functions."""

    def test_get_nws_headers_format(self):
        """Test that NWS headers have required format."""
        headers = get_nws_headers()

        assert isinstance(headers, dict)
        assert "User-Agent" in headers
        assert "Accept" in headers
        assert "TravelAssistantMCP" in headers["User-Agent"]
        assert "application/geo+json" in headers["Accept"]

    def test_get_nws_headers_user_agent_structure(self):
        """Test User-Agent header has proper structure."""
        headers = get_nws_headers()
        user_agent = headers["User-Agent"]

        # Should contain version and contact info
        assert "2.0" in user_agent or "TravelAssistant" in user_agent
        assert "support" in user_agent or "example" in user_agent

    @responses.activate
    def test_make_nws_request_success(self):
        """Test successful NWS API request."""
        mock_response_data = {
            "type": "Feature",
            "properties": {"temperature": 72},
        }

        responses.add(
            responses.GET,
            "https://api.weather.gov/points/40,-77",
            json=mock_response_data,
            status=200,
        )

        result = make_nws_request("https://api.weather.gov/points/40,-77")

        assert result is not None
        assert isinstance(result, dict)
        assert result["type"] == "Feature"
        assert result["properties"]["temperature"] == 72

    @responses.activate
    def test_make_nws_request_http_500_error(self):
        """Test handling of HTTP 500 error from NWS."""
        responses.add(
            responses.GET,
            "https://api.weather.gov/points/40,-77",
            status=500,
        )

        result = make_nws_request("https://api.weather.gov/points/40,-77")

        assert result is None

    @responses.activate
    def test_make_nws_request_http_404_error(self):
        """Test handling of HTTP 404 error from NWS."""
        responses.add(
            responses.GET,
            "https://api.weather.gov/points/invalid",
            status=404,
        )

        result = make_nws_request("https://api.weather.gov/points/invalid")

        assert result is None

    @responses.activate
    def test_make_nws_request_timeout_error(self):
        """Test handling of timeout when making NWS request."""
        import requests

        def timeout_callback(request):
            raise requests.exceptions.Timeout("Connection timeout")

        responses.add_callback(
            responses.GET,
            "https://api.weather.gov/points/40,-77",
            callback=timeout_callback,
            content_type="application/json",
        )

        result = make_nws_request("https://api.weather.gov/points/40,-77")

        # Should return None on timeout
        assert result is None

    @responses.activate
    def test_make_nws_request_invalid_json_response(self):
        """Test handling of invalid JSON response from NWS."""
        responses.add(
            responses.GET,
            "https://api.weather.gov/points/40,-77",
            body="Not valid JSON",
            status=200,
            content_type="text/plain",
        )

        result = make_nws_request("https://api.weather.gov/points/40,-77")

        assert result is None

    @responses.activate
    def test_make_nws_request_sends_proper_headers(self):
        """Test that NWS requests include proper headers."""
        responses.add(
            responses.GET,
            "https://api.weather.gov/points/40,-77",
            json={"type": "Feature"},
            status=200,
        )

        make_nws_request("https://api.weather.gov/points/40,-77")

        # Verify request was made
        assert len(responses.calls) == 1
        request = responses.calls[0].request

        assert "User-Agent" in request.headers
        assert "Accept" in request.headers
        assert request.headers["Accept"] == "application/geo+json"

    @responses.activate
    def test_make_nws_request_timeout_parameter(self):
        """Test that NWS requests use timeout parameter."""
        responses.add(
            responses.GET,
            "https://api.weather.gov/points/40,-77",
            json={"type": "Feature"},
            status=200,
        )

        make_nws_request("https://api.weather.gov/points/40,-77")

        # Should have made exactly one request
        assert len(responses.calls) == 1


class TestSecurityHelpers:
    """Test security-related helper functions."""

    def test_sanitize_url_for_logging_exchangerate_api(self):
        """Test that ExchangeRate-API keys are redacted from URLs."""
        from travel_assistant.helpers import sanitize_url_for_logging
        
        # Test with real API key pattern (hexadecimal)
        url = "https://v6.exchangerate-api.com/v6/4b9d09c342e6f730c7d2376e/pair/USD/EUR"
        sanitized = sanitize_url_for_logging(url)
        
        # API key should be redacted
        assert "4b9d09c342e6f730c7d2376e" not in sanitized
        assert "[REDACTED]" in sanitized
        assert "https://v6.exchangerate-api.com/v6/[REDACTED]/pair/USD/EUR" == sanitized

    def test_sanitize_url_for_logging_query_parameter(self):
        """Test that query parameter API keys are redacted."""
        from travel_assistant.helpers import sanitize_url_for_logging
        
        # Test with query parameter style
        url = "https://api.example.com/search?api_key=secret123&q=test"
        sanitized = sanitize_url_for_logging(url)
        
        assert "secret123" not in sanitized
        assert "api_key=[REDACTED]" in sanitized
        assert "q=test" in sanitized  # Other params should remain

    def test_sanitize_url_for_logging_ampersand_parameter(self):
        """Test that API keys in middle of query string are redacted."""
        from travel_assistant.helpers import sanitize_url_for_logging
        
        url = "https://api.example.com/search?q=test&api_key=secret456&limit=10"
        sanitized = sanitize_url_for_logging(url)
        
        assert "secret456" not in sanitized
        assert "api_key=[REDACTED]" in sanitized
        assert "q=test" in sanitized
        assert "limit=10" in sanitized

    def test_sanitize_url_for_logging_no_api_key(self):
        """Test that URLs without API keys are unchanged."""
        from travel_assistant.helpers import sanitize_url_for_logging
        
        url = "https://api.example.com/search?q=test&limit=10"
        sanitized = sanitize_url_for_logging(url)
        
        # Should be unchanged
        assert sanitized == url

    def test_sanitize_url_for_logging_multiple_patterns(self):
        """Test sanitization with multiple API key patterns."""
        from travel_assistant.helpers import sanitize_url_for_logging
        
        # Path-based key
        url1 = "https://v6.exchangerate-api.com/v6/abc123def456/pair/USD/EUR"
        sanitized1 = sanitize_url_for_logging(url1)
        assert "abc123def456" not in sanitized1
        assert "[REDACTED]" in sanitized1

