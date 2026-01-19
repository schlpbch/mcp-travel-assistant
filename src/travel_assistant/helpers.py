"""Utility functions for the Travel Assistant MCP server."""

import os
import uuid
import requests
from typing import Dict, Optional, Any

from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter


def get_serpapi_key() -> str:
    """Get SerpAPI key from environment variable."""
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        raise ValueError("SERPAPI_KEY environment variable is required")
    return api_key


def get_exchange_rate_api_key() -> str:
    """Get ExchangeRate-API key from environment variable."""
    api_key = os.getenv("EXCHANGE_RATE_API_KEY")
    if not api_key:
        raise ValueError("EXCHANGE_RATE_API_KEY environment variable is required")
    return api_key


def get_geolocator():
    """Initialize and return a geolocator with rate limiting."""
    email_identifier = f"{uuid.uuid4()}.com"
    geolocator = Nominatim(user_agent=email_identifier)
    return (
        RateLimiter(geolocator.geocode, min_delay_seconds=1),
        RateLimiter(geolocator.reverse, min_delay_seconds=1),
    )


def get_nws_headers() -> Dict[str, str]:
    """Get headers for NWS API requests with required User-Agent."""
    return {
        "User-Agent": "TravelAssistantMCP/2.0 (travel-assistant, support@example.com)",
        "Accept": "application/geo+json",
    }


def make_nws_request(endpoint: str) -> Optional[Dict[str, Any]]:
    """Make a request to the NWS API with proper error handling."""
    try:
        response = requests.get(endpoint, headers=get_nws_headers(), timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error making request to {endpoint}: {str(e)}")
        return None
