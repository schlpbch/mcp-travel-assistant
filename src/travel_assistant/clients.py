"""API client wrappers for the Travel Assistant MCP server."""

import json
import requests
from typing import Dict, Any, Optional
from datetime import datetime

from amadeus import Client as AmadeusClient, ResponseError

from .helpers import (
    get_serpapi_key,
    get_exchange_rate_api_key,
    get_geolocator,
)


# =====================================================================
# SERPAPI CLIENT
# =====================================================================

class SerpAPIClient:
    """Client for Google Flights, Hotels, Events, and Finance via SerpAPI."""

    def __init__(self):
        self.base_url = "https://serpapi.com/search"
        try:
            self.api_key = get_serpapi_key()
        except ValueError:
            self.api_key = None

    def _request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make a request to SerpAPI."""
        if not self.api_key:
            return {"error": "SERPAPI_KEY environment variable not set"}
        params["api_key"] = self.api_key
        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": f"SerpAPI request failed: {str(e)}"}

    def search_flights(self, **params) -> Dict[str, Any]:
        """Search for flights using Google Flights."""
        params["engine"] = "google_flights"
        return self._request(params)

    def search_hotels(self, **params) -> Dict[str, Any]:
        """Search for hotels using Google Hotels."""
        params["engine"] = "google_hotels"
        return self._request(params)

    def search_events(self, **params) -> Dict[str, Any]:
        """Search for events using Google Events."""
        params["engine"] = "google_events"
        return self._request(params)

    def lookup_stock(self, **params) -> Dict[str, Any]:
        """Look up stock information using Google Finance."""
        params["engine"] = "google_finance"
        return self._request(params)


# =====================================================================
# AMADEUS CLIENT WRAPPER
# =====================================================================

class AmadeusClientWrapper:
    """Wrapper around Amadeus SDK client."""

    def __init__(self, amadeus_client: AmadeusClient):
        """Initialize with an Amadeus client instance."""
        self.client = amadeus_client

    def search_flights(self, **params) -> str:
        """Search for flights using Amadeus GDS."""
        try:
            # Validate passenger counts
            adults = params.get("adults", 1)
            children = params.get("children", 0) or 0
            infants = params.get("infants", 0) or 0

            if not (1 <= adults <= 9):
                return json.dumps({"error": "Adults must be between 1 and 9"})

            if children and infants and (adults + children > 9):
                return json.dumps({"error": "Total seated travelers cannot exceed 9"})

            if infants and (infants > adults):
                return json.dumps({"error": "Infants cannot exceed adults"})

            response = self.client.shopping.flight_offers_search.get(**params)
            result = response.body
            result["provider"] = "Amadeus GDS"
            result["search_timestamp"] = datetime.now().isoformat()
            return json.dumps(result)
        except ResponseError as e:
            return json.dumps({"error": f"Amadeus API error: {str(e)}"})
        except Exception as e:
            return json.dumps({"error": f"Unexpected error: {str(e)}"})

    def search_hotels_by_city(self, **params) -> str:
        """Search for hotels by city using Amadeus."""
        try:
            response = self.client.reference_data.locations.hotels.by_city.get(**params)
            result = response.body
            result["provider"] = "Amadeus GDS"
            result["search_timestamp"] = datetime.now().isoformat()
            return json.dumps(result)
        except ResponseError as e:
            return json.dumps({"error": f"Amadeus API error: {str(e)}"})
        except Exception as e:
            return json.dumps({"error": f"Unexpected error: {str(e)}"})

    def search_hotels_by_geocode(self, **params) -> str:
        """Search for hotels by coordinates using Amadeus."""
        try:
            response = self.client.reference_data.locations.hotels.by_geocode.get(**params)
            result = response.body
            result["provider"] = "Amadeus GDS"
            result["search_timestamp"] = datetime.now().isoformat()
            return json.dumps(result)
        except ResponseError as e:
            return json.dumps({"error": f"Amadeus API error: {str(e)}"})
        except Exception as e:
            return json.dumps({"error": f"Unexpected error: {str(e)}"})

    def search_hotel_offers(self, **params) -> str:
        """Search for hotel offers (real-time availability) using Amadeus."""
        if not params.get("cityCode") and not params.get("hotelIds"):
            return json.dumps({"error": "Either cityCode or hotelIds must be provided"})

        try:
            response = self.client.shopping.hotel_offers.get(**params)
            result = response.body
            result["provider"] = "Amadeus GDS"
            result["search_timestamp"] = datetime.now().isoformat()
            return json.dumps(result)
        except ResponseError as e:
            return json.dumps({"error": f"Amadeus API error: {str(e)}"})
        except Exception as e:
            return json.dumps({"error": f"Unexpected error: {str(e)}"})

    def search_activities(self, **params) -> str:
        """Search for activities/tours using Amadeus."""
        try:
            response = self.client.shopping.activities.get(**params)
            result = response.body
            result["provider"] = "Amadeus GDS"
            result["search_timestamp"] = datetime.now().isoformat()
            return json.dumps(result)
        except ResponseError as e:
            return json.dumps({"error": f"Amadeus API error: {str(e)}"})
        except AttributeError as e:
            return json.dumps({
                "error": f"Tours and Activities API not available: {str(e)}",
                "note": "This API might require a newer SDK version or special access"
            })
        except Exception as e:
            return json.dumps({"error": f"Unexpected error: {str(e)}"})

    def get_activity_details(self, activity_id: str) -> str:
        """Get details for a specific activity using Amadeus."""
        try:
            response = self.client.shopping.activity(activity_id).get()
            result = response.body
            result["provider"] = "Amadeus GDS"
            result["search_timestamp"] = datetime.now().isoformat()
            return json.dumps(result)
        except ResponseError as e:
            return json.dumps({"error": f"Amadeus API error: {str(e)}"})
        except AttributeError as e:
            return json.dumps({
                "error": f"Tours and Activities API not available: {str(e)}",
                "note": "This API might require a newer SDK version or special access"
            })
        except Exception as e:
            return json.dumps({"error": f"Unexpected error: {str(e)}"})


# =====================================================================
# EXCHANGERATE API CLIENT
# =====================================================================

class ExchangeRateClient:
    """Client for currency conversion via ExchangeRate-API."""

    def __init__(self):
        self.base_url = "https://v6.exchangerate-api.com/v6"
        try:
            self.api_key = get_exchange_rate_api_key()
        except ValueError:
            self.api_key = None

    def convert(self, from_currency: str, to_currency: str, amount: float = 1.0) -> Dict[str, Any]:
        """Convert between currencies."""
        if not self.api_key:
            return {"error": "EXCHANGE_RATE_API_KEY environment variable not set"}
        url = f"{self.base_url}/{self.api_key}/pair/{from_currency.upper()}/{to_currency.upper()}"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get("result") != "success":
                return {"error": data.get("error-type") or "ExchangeRate-API error"}

            rate = data.get("conversion_rate")
            if rate is None:
                return {"error": "Conversion rate not available"}

            converted = round(amount * float(rate), 2)

            return {
                "from_currency": from_currency.upper(),
                "to_currency": to_currency.upper(),
                "amount": amount,
                "exchange_rate": rate,
                "converted_amount": converted,
                "search_timestamp": datetime.now().isoformat(),
                "provider": "exchangerate-api",
            }
        except requests.exceptions.RequestException as e:
            return {"error": f"Currency API request failed: {str(e)}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}


# =====================================================================
# NOMINATIM GEOCODING CLIENT
# =====================================================================

class GeocodingClient:
    """Client for geocoding and reverse geocoding via Nominatim."""

    def __init__(self):
        self.geocode_limiter, self.reverse_limiter = get_geolocator()

    def geocode(
        self,
        location: str,
        exactly_one: bool = True,
        timeout: int = 10,
        language: str = "en",
        addressdetails: bool = True,
        country_codes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Geocode a location name to coordinates."""
        try:
            params = {
                "exactly_one": exactly_one,
                "timeout": timeout,
                "language": language,
                "addressdetails": addressdetails,
            }

            if country_codes:
                params["country_codes"] = country_codes.split(",")

            result = self.geocode_limiter(location, **params)

            if not result:
                return {
                    "error": f"Location '{location}' not found",
                    "suggestions": "Try using a more specific address or landmark name",
                }

            if exactly_one:
                return {
                    "location": location,
                    "latitude": float(result.latitude),
                    "longitude": float(result.longitude),
                    "address": result.address,
                    "search_timestamp": datetime.now().isoformat(),
                }
            else:
                return {
                    "location": location,
                    "results": [
                        {
                            "latitude": float(r.latitude),
                            "longitude": float(r.longitude),
                            "address": r.address,
                        }
                        for r in result
                    ],
                    "search_timestamp": datetime.now().isoformat(),
                }
        except Exception as e:
            return {"error": f"Geocoding error: {str(e)}"}

    def reverse_geocode(
        self, latitude: float, longitude: float, language: str = "en"
    ) -> Dict[str, Any]:
        """Reverse geocode coordinates to location."""
        try:
            params = {
                "language": language,
            }

            result = self.reverse_limiter((latitude, longitude), **params)

            if not result:
                return {"error": f"No location found for coordinates {latitude}, {longitude}"}

            return {
                "latitude": latitude,
                "longitude": longitude,
                "address": result.address,
                "search_timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            return {"error": f"Reverse geocoding error: {str(e)}"}
