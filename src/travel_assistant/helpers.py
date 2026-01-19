"""Utility functions for the Travel Assistant MCP server."""

import os
import uuid
import requests
from typing import Dict, Optional, Any
from datetime import datetime

from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

# Module-level geolocator (initialized once, reused across requests)
_GEOLOCATOR_INSTANCE = None


def _get_or_create_geolocator():
    """Get or create a module-level geolocator instance (lazy initialization)."""
    global _GEOLOCATOR_INSTANCE
    if _GEOLOCATOR_INSTANCE is None:
        email_identifier = f"{uuid.uuid4()}.com"
        geolocator = Nominatim(user_agent=email_identifier)
        _GEOLOCATOR_INSTANCE = (
            RateLimiter(geolocator.geocode, min_delay_seconds=1),
            RateLimiter(geolocator.reverse, min_delay_seconds=1),
        )
    return _GEOLOCATOR_INSTANCE


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
    """Get geolocator with rate limiting (cached across requests)."""
    return _get_or_create_geolocator()


def format_amadeus_response(response_body: Dict[str, Any]) -> Dict[str, Any]:
    """Format Amadeus API response with metadata.

    Args:
        response_body: Raw response body from Amadeus API

    Returns:
        Formatted response dict with provider and timestamp
    """
    result = response_body.copy() if isinstance(response_body, dict) else response_body
    result["provider"] = "Amadeus GDS"
    result["search_timestamp"] = datetime.now().isoformat()
    return result


def format_error_response(error_msg: str) -> Dict[str, str]:
    """Format error response consistently across all tools.

    Args:
        error_msg: Error message string

    Returns:
        Standardized error dict
    """
    return {"error": error_msg}


def build_optional_params(
    required_params: Dict[str, Any],
    optional_params: Dict[str, Any],
    none_check_fields: Optional[set] = None
) -> Dict[str, Any]:
    """Build API parameter dict with optional parameter handling.

    Handles two types of optional parameters:
    - Truthy check: Empty strings/None values excluded (default)
    - None check: Only None excluded, 0/False values included (for numeric/bool)

    Args:
        required_params: Dict of required parameters (always included)
        optional_params: Dict of all optional parameters with their values
        none_check_fields: Set of field names requiring 'is not None' check
                          (for numeric/bool types where 0/False are valid)

    Returns:
        Complete parameter dict ready for API calls
    """
    params = required_params.copy()
    none_check_set = none_check_fields or set()

    for key, value in optional_params.items():
        if key in none_check_set:
            if value is not None:
                params[key] = value
        else:
            if value:  # Truthy check for strings/None filtering
                params[key] = value

    return params


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
