"""Tests for travel_assistant.clients module."""
import pytest
import json
import responses
from unittest.mock import Mock, patch
from datetime import datetime

from travel_assistant.clients import (
    SerpAPIClient,
    AmadeusClientWrapper,
    ExchangeRateClient,
    GeocodingClient,
)


# =====================================================================
# SERPAPI CLIENT TESTS
# =====================================================================


class TestSerpAPIClient:
    """Test SerpAPIClient for flights, hotels, events, and finance."""

    def test_serpapi_client_initialization(self):
        """Test SerpAPIClient initializes with correct base URL."""
        client = SerpAPIClient()
        assert client.base_url == "https://serpapi.com/search"
        assert client.api_key is not None

    @responses.activate
    def test_search_flights_success(self):
        """Test successful flight search via SerpAPI."""
        mock_response = {
            "best_flights": [
                {"price": 299, "airline": "Delta", "stops": 0}
            ],
            "other_flights": [],
            "price_insights": {"lowest": 299, "highest": 599},
        }

        responses.add(
            responses.GET,
            "https://serpapi.com/search",
            json=mock_response,
            status=200,
        )

        client = SerpAPIClient()
        result = client.search_flights(
            departure_id="JFK",
            arrival_id="LAX",
            outbound_date="2025-06-15",
        )

        assert "best_flights" in result
        assert len(result["best_flights"]) == 1
        assert result["best_flights"][0]["price"] == 299

    @responses.activate
    def test_search_flights_http_500_error(self):
        """Test handling of HTTP 500 error from SerpAPI."""
        responses.add(
            responses.GET,
            "https://serpapi.com/search",
            status=500,
        )

        client = SerpAPIClient()
        result = client.search_flights(
            departure_id="JFK",
            arrival_id="LAX",
            outbound_date="2025-06-15",
        )

        assert "error" in result
        assert "failed" in result["error"].lower() or "500" in str(result)

    @responses.activate
    def test_search_flights_http_404_error(self):
        """Test handling of HTTP 404 error from SerpAPI."""
        responses.add(
            responses.GET,
            "https://serpapi.com/search",
            status=404,
        )

        client = SerpAPIClient()
        result = client.search_flights(
            departure_id="INVALID",
            arrival_id="INVALID",
            outbound_date="2025-06-15",
        )

        assert "error" in result

    @responses.activate
    def test_search_flights_timeout_error(self):
        """Test handling of timeout when searching flights."""
        import requests

        def timeout_callback(request):
            raise requests.exceptions.Timeout("Connection timeout")

        responses.add_callback(
            responses.GET,
            "https://serpapi.com/search",
            callback=timeout_callback,
            content_type="application/json",
        )

        client = SerpAPIClient()
        result = client.search_flights(
            departure_id="JFK",
            arrival_id="LAX",
            outbound_date="2025-06-15",
        )

        assert "error" in result

    @responses.activate
    def test_search_hotels_success(self):
        """Test successful hotel search via SerpAPI."""
        mock_response = {
            "hotels": [
                {
                    "name": "Hotel A",
                    "price": "$150",
                    "rating": 4.5,
                }
            ]
        }

        responses.add(
            responses.GET,
            "https://serpapi.com/search",
            json=mock_response,
            status=200,
        )

        client = SerpAPIClient()
        result = client.search_hotels(
            location="Paris",
            check_in_date="2025-06-15",
            check_out_date="2025-06-20",
        )

        assert "hotels" in result
        assert result["hotels"][0]["name"] == "Hotel A"

    @responses.activate
    def test_search_events_success(self):
        """Test successful event search via SerpAPI."""
        mock_response = {
            "events": [
                {"title": "Concert", "date": "2025-06-20", "venue": "Madison Square Garden"}
            ]
        }

        responses.add(
            responses.GET,
            "https://serpapi.com/search",
            json=mock_response,
            status=200,
        )

        client = SerpAPIClient()
        result = client.search_events(query="concerts", location="NYC")

        assert "events" in result

    @responses.activate
    def test_lookup_stock_success(self):
        """Test successful stock lookup via SerpAPI."""
        mock_response = {
            "stocks": [
                {"symbol": "DAL", "price": 45.50, "change": 0.75}
            ]
        }

        responses.add(
            responses.GET,
            "https://serpapi.com/search",
            json=mock_response,
            status=200,
        )

        client = SerpAPIClient()
        result = client.lookup_stock(symbol="DAL")

        assert "stocks" in result


# =====================================================================
# AMADEUS CLIENT WRAPPER TESTS
# =====================================================================


class TestAmadeusClientWrapper:
    """Test AmadeusClientWrapper for flight and hotel searches."""

    def test_amadeus_client_wrapper_initialization(self):
        """Test AmadeusClientWrapper initializes with client."""
        mock_amadeus = Mock()
        wrapper = AmadeusClientWrapper(mock_amadeus)
        assert wrapper.client is mock_amadeus

    def test_search_flights_success(self):
        """Test successful flight search via Amadeus."""
        mock_amadeus = Mock()
        mock_response = Mock()
        mock_response.body = {
            "data": [
                {"id": "1", "instantTicketingRequired": False, "nonHomogeneous": False}
            ]
        }
        mock_amadeus.shopping.flight_offers_search.get.return_value = mock_response

        wrapper = AmadeusClientWrapper(mock_amadeus)
        result_str = wrapper.search_flights(
            originLocationCode="JFK",
            destinationLocationCode="LAX",
            departureDate="2025-06-15",
            adults=1,
        )

        result = json.loads(result_str)
        assert "data" in result
        assert result["provider"] == "Amadeus GDS"
        assert "search_timestamp" in result

    def test_search_flights_invalid_adults_too_many(self):
        """Test search_flights validates adults count (max 9)."""
        mock_amadeus = Mock()
        wrapper = AmadeusClientWrapper(mock_amadeus)

        result_str = wrapper.search_flights(
            originLocationCode="JFK",
            destinationLocationCode="LAX",
            departureDate="2025-06-15",
            adults=10,  # Invalid
        )

        result = json.loads(result_str)
        assert "error" in result
        assert "adults" in result["error"].lower()

    def test_search_flights_invalid_adults_zero(self):
        """Test search_flights validates adults count (min 1)."""
        mock_amadeus = Mock()
        wrapper = AmadeusClientWrapper(mock_amadeus)

        result_str = wrapper.search_flights(
            originLocationCode="JFK",
            destinationLocationCode="LAX",
            departureDate="2025-06-15",
            adults=0,  # Invalid
        )

        result = json.loads(result_str)
        assert "error" in result

    def test_search_flights_infants_exceed_adults(self):
        """Test search_flights validates infants <= adults."""
        mock_amadeus = Mock()
        wrapper = AmadeusClientWrapper(mock_amadeus)

        result_str = wrapper.search_flights(
            originLocationCode="JFK",
            destinationLocationCode="LAX",
            departureDate="2025-06-15",
            adults=1,
            infants=2,  # Invalid: more infants than adults
        )

        result = json.loads(result_str)
        assert "error" in result
        assert "infant" in result["error"].lower()

    def test_search_flights_amadeus_error(self):
        """Test handling of Amadeus API errors."""
        from amadeus import ResponseError

        mock_amadeus = Mock()
        # Create a mock response for ResponseError
        mock_response = Mock()
        mock_response.parsed = False
        mock_response.status_code = 400

        mock_amadeus.shopping.flight_offers_search.get.side_effect = ResponseError(
            mock_response
        )

        wrapper = AmadeusClientWrapper(mock_amadeus)
        result_str = wrapper.search_flights(
            originLocationCode="JFK",
            destinationLocationCode="LAX",
            departureDate="2025-06-15",
            adults=1,
        )

        result = json.loads(result_str)
        assert "error" in result

    def test_search_hotels_by_city_success(self):
        """Test successful hotel search by city via Amadeus."""
        mock_amadeus = Mock()
        mock_response = Mock()
        mock_response.body = {"data": [{"hotelId": "PARXYZ", "name": "Hotel Paris"}]}
        mock_amadeus.reference_data.locations.hotels.by_city.get.return_value = mock_response

        wrapper = AmadeusClientWrapper(mock_amadeus)
        result_str = wrapper.search_hotels_by_city(cityCode="PAR")

        result = json.loads(result_str)
        assert "data" in result
        assert result["provider"] == "Amadeus GDS"

    def test_search_hotels_by_geocode_success(self):
        """Test successful hotel search by coordinates via Amadeus."""
        mock_amadeus = Mock()
        mock_response = Mock()
        mock_response.body = {"data": [{"hotelId": "PARXYZ"}]}
        mock_amadeus.reference_data.locations.hotels.by_geocode.get.return_value = mock_response

        wrapper = AmadeusClientWrapper(mock_amadeus)
        result_str = wrapper.search_hotels_by_geocode(latitude=48.8566, longitude=2.3522)

        result = json.loads(result_str)
        assert "data" in result

    def test_search_hotel_offers_requires_city_or_hotel_ids(self):
        """Test search_hotel_offers requires cityCode or hotelIds."""
        mock_amadeus = Mock()
        wrapper = AmadeusClientWrapper(mock_amadeus)

        result_str = wrapper.search_hotel_offers()

        result = json.loads(result_str)
        assert "error" in result
        assert "cityCode" in result["error"] or "hotelIds" in result["error"]

    def test_search_hotel_offers_success(self):
        """Test successful hotel offer search via Amadeus."""
        mock_amadeus = Mock()
        mock_response = Mock()
        mock_response.body = {"data": [{"id": "XYZHOTEL"}]}
        mock_amadeus.shopping.hotel_offers.get.return_value = mock_response

        wrapper = AmadeusClientWrapper(mock_amadeus)
        result_str = wrapper.search_hotel_offers(cityCode="PAR", checkInDate="2025-06-15")

        result = json.loads(result_str)
        assert "data" in result
        assert result["provider"] == "Amadeus GDS"

    def test_search_activities_success(self):
        """Test successful activity search via Amadeus."""
        mock_amadeus = Mock()
        mock_response = Mock()
        mock_response.body = {"data": [{"id": "123456", "name": "Eiffel Tower Tour"}]}
        mock_amadeus.shopping.activities.get.return_value = mock_response

        wrapper = AmadeusClientWrapper(mock_amadeus)
        result_str = wrapper.search_activities(latitude=48.8566, longitude=2.3522)

        result = json.loads(result_str)
        assert "data" in result

    def test_search_activities_not_available_error(self):
        """Test handling when Activities API is not available."""
        mock_amadeus = Mock()
        mock_amadeus.shopping.activities.get.side_effect = AttributeError(
            "API not available"
        )

        wrapper = AmadeusClientWrapper(mock_amadeus)
        result_str = wrapper.search_activities(latitude=48.8566, longitude=2.3522)

        result = json.loads(result_str)
        assert "error" in result


# =====================================================================
# EXCHANGE RATE CLIENT TESTS
# =====================================================================


class TestExchangeRateClient:
    """Test ExchangeRateClient for currency conversion."""

    def test_exchange_rate_client_initialization(self):
        """Test ExchangeRateClient initializes with correct base URL."""
        client = ExchangeRateClient()
        assert "exchangerate-api.com" in client.base_url

    @responses.activate
    def test_convert_success(self):
        """Test successful currency conversion."""
        mock_response = {
            "result": "success",
            "conversion_rate": 0.92,
        }

        responses.add(
            responses.GET,
            "https://v6.exchangerate-api.com/v6/test-exchange-key-12345/pair/USD/EUR",
            json=mock_response,
            status=200,
        )

        client = ExchangeRateClient()
        result = client.convert("USD", "EUR", 100.0)

        assert "exchange_rate" in result
        assert result["converted_amount"] == 92.0
        assert result["provider"] == "exchangerate-api"
        # After rounding, the value should be 92.0
        assert abs(result["converted_amount"] - 92.0) < 0.01

    @responses.activate
    def test_convert_default_amount(self):
        """Test currency conversion with default amount (1.0)."""
        mock_response = {
            "result": "success",
            "conversion_rate": 0.92,
        }

        responses.add(
            responses.GET,
            "https://v6.exchangerate-api.com/v6/test-exchange-key-12345/pair/USD/EUR",
            json=mock_response,
            status=200,
        )

        client = ExchangeRateClient()
        result = client.convert("USD", "EUR")

        assert result["amount"] == 1.0
        assert result["converted_amount"] == 0.92

    @responses.activate
    def test_convert_case_insensitive(self):
        """Test currency codes are converted to uppercase."""
        mock_response = {
            "result": "success",
            "conversion_rate": 0.92,
        }

        responses.add(
            responses.GET,
            "https://v6.exchangerate-api.com/v6/test-exchange-key-12345/pair/USD/EUR",
            json=mock_response,
            status=200,
        )

        client = ExchangeRateClient()
        result = client.convert("usd", "eur", 100.0)

        assert result["from_currency"] == "USD"
        assert result["to_currency"] == "EUR"

    @responses.activate
    def test_convert_api_error(self):
        """Test handling of API error from ExchangeRate-API."""
        mock_response = {
            "result": "error",
            "error-type": "invalid-key",
        }

        responses.add(
            responses.GET,
            "https://v6.exchangerate-api.com/v6/test-exchange-key-12345/pair/USD/EUR",
            json=mock_response,
            status=200,
        )

        client = ExchangeRateClient()
        result = client.convert("USD", "EUR")

        assert "error" in result

    @responses.activate
    def test_convert_http_error(self):
        """Test handling of HTTP error."""
        responses.add(
            responses.GET,
            "https://v6.exchangerate-api.com/v6/test-exchange-key-12345/pair/USD/EUR",
            status=503,
        )

        client = ExchangeRateClient()
        result = client.convert("USD", "EUR")

        assert "error" in result

# =====================================================================
# GEOCODING CLIENT TESTS
# =====================================================================


class TestGeocodingClient:
    """Test GeocodingClient for geocoding and reverse geocoding."""

    def test_geocoding_client_initialization(self):
        """Test GeocodingClient initializes with geolocator."""
        client = GeocodingClient()
        assert client.geocode_limiter is not None
        assert client.reverse_limiter is not None

    def test_geocode_success(self):
        """Test successful geocoding."""
        # Mock the geocode_limiter
        mock_result = Mock()
        mock_result.latitude = 48.8566
        mock_result.longitude = 2.3522
        mock_result.address = "Paris, France"

        client = GeocodingClient()
        client.geocode_limiter = Mock(return_value=mock_result)

        result = client.geocode("Paris")

        assert result["location"] == "Paris"
        assert result["latitude"] == 48.8566
        assert result["longitude"] == 2.3522
        assert result["address"] == "Paris, France"
        assert "search_timestamp" in result

    def test_geocode_not_found(self):
        """Test geocoding when location is not found."""
        client = GeocodingClient()
        client.geocode_limiter = Mock(return_value=None)

        result = client.geocode("InvalidLocationXYZ")

        assert "error" in result
        assert "not found" in result["error"].lower()

    def test_geocode_multiple_results(self):
        """Test geocoding with multiple results."""
        mock_result1 = Mock()
        mock_result1.latitude = 48.8566
        mock_result1.longitude = 2.3522
        mock_result1.address = "Paris, France"

        mock_result2 = Mock()
        mock_result2.latitude = 48.7500
        mock_result2.longitude = 2.1700
        mock_result2.address = "Paris, Texas, USA"

        client = GeocodingClient()
        client.geocode_limiter = Mock(return_value=[mock_result1, mock_result2])

        result = client.geocode("Paris", exactly_one=False)

        assert result["location"] == "Paris"
        assert "results" in result
        assert len(result["results"]) == 2

    def test_reverse_geocode_success(self):
        """Test successful reverse geocoding."""
        mock_result = Mock()
        mock_result.address = "Paris, France"

        client = GeocodingClient()
        client.reverse_limiter = Mock(return_value=mock_result)

        result = client.reverse_geocode(48.8566, 2.3522)

        assert result["latitude"] == 48.8566
        assert result["longitude"] == 2.3522
        assert result["address"] == "Paris, France"
        assert "search_timestamp" in result

    def test_reverse_geocode_not_found(self):
        """Test reverse geocoding when address not found."""
        client = GeocodingClient()
        # Mock returns None when address not found
        client.reverse_limiter = Mock(return_value=None)

        result = client.reverse_geocode(0.0, 0.0)

        assert "error" in result
        # The error might be "not found" or a variation
        assert isinstance(result["error"], str)
