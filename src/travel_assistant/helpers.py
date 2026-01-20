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


# =====================================================================
# VALIDATION HELPERS
# =====================================================================

def validate_date_format(date_str: str, field_name: str = "date") -> str:
    """Validate date is in YYYY-MM-DD format.

    Args:
        date_str: Date string to validate
        field_name: Name of the field (for error messages)

    Returns:
        Validated date string

    Raises:
        ValueError: If date format is invalid
    """
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return date_str
    except ValueError:
        raise ValueError(f"{field_name} must be in YYYY-MM-DD format")


def validate_currency_code(code: str) -> str:
    """Validate currency code is 3 uppercase letters (ISO 4217).

    Args:
        code: Currency code to validate (e.g., 'USD', 'EUR')

    Returns:
        Uppercase currency code

    Raises:
        ValueError: If currency code format is invalid
    """
    if not code or len(code) != 3 or not code.isalpha():
        raise ValueError("Currency code must be 3 letters (e.g., USD, EUR, GBP)")
    return code.upper()


# =====================================================================
# ACCESSIBILITY HELPERS
# =====================================================================

def extract_hotel_accessibility(hotel_property: Dict[str, Any]) -> Dict[str, Any]:
    """Extract accessibility information from SerpAPI hotel property.

    SerpAPI includes amenities with IDs. Amenity ID 53 = wheelchair accessible.

    Args:
        hotel_property: Hotel property dict from SerpAPI response

    Returns:
        Dictionary with accessibility information
    """
    amenities = hotel_property.get("amenities", [])
    amenity_ids = [a.get("id") for a in amenities if isinstance(a, dict) and "id" in a]

    wheelchair_accessible = 53 in amenity_ids

    return {
        "wheelchair_accessible": wheelchair_accessible,
        "accessible_room_available": wheelchair_accessible,
        "wheelchair_amenity_id": 53,
        "amenities": amenities,
    }


def extract_amadeus_hotel_accessibility(hotel_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract accessibility information from Amadeus hotel offer.

    Amadeus returns facility and description data that may contain accessibility info.

    Args:
        hotel_data: Hotel data dict from Amadeus API response

    Returns:
        Dictionary with accessibility information
    """
    facilities = hotel_data.get("facilities", [])
    descriptions = hotel_data.get("descriptions", {})

    # Build facility list from facilities array
    facility_list = []
    if facilities:
        for facility in facilities:
            if isinstance(facility, dict):
                facility_list.append(facility.get("description", str(facility)))
            else:
                facility_list.append(str(facility))

    # Check for accessibility-related facilities
    accessibility_keywords = [
        "wheelchair",
        "accessible",
        "mobility",
        "elevator",
        "ramp",
        "parking",
        "bathroom",
    ]

    has_accessibility = any(
        keyword.lower() in str(facility).lower() for facility in facility_list
        for keyword in accessibility_keywords
    )

    return {
        "wheelchair_accessible": has_accessibility,
        "accessible_room_available": has_accessibility,
        "facility_list": facility_list,
    }


def extract_flight_accessibility_from_amadeus(flight_offer: Dict[str, Any]) -> Dict[str, Any]:
    """Extract accessibility information from Amadeus flight offer.

    Amadeus returns traveler pricing which may include special service requests (SSR).

    Args:
        flight_offer: Flight offer dict from Amadeus API response

    Returns:
        Dictionary with accessibility information and SSR codes
    """
    ssr_codes = []

    # Extract SSR codes from traveler pricing if available
    traveler_pricings = flight_offer.get("travelerPricings", [])
    for pricing in traveler_pricings:
        fare_details = pricing.get("fareDetailsBySegment", [])
        for detail in fare_details:
            included_checks = detail.get("includedCheckedBags", {})
            # SSR codes are not typically in the response, but could be passed by user
            # This is a placeholder for extracting them if available in extended response
            pass

    return {
        "wheelchair_available": False,
        "wheelchair_stowage": False,
        "accessible_lavatory": False,
        "extra_legroom_available": False,
        "special_service_codes": ssr_codes if ssr_codes else None,
        "companion_required": None,
        "special_meals_available": False,
        "notes": "Check with airline for specific accessibility accommodations",
    }
