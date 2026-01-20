"""Tests for travel_assistant.models module."""

import pytest
from datetime import datetime, timedelta
from pydantic import ValidationError
from travel_assistant.models import (
    AppContext,
    FlightSearchParams,
    AmadeusFlightSearchParams,
    HotelSearchParams,
    AmadeusHotelOfferParams,
    EventSearchParams,
    ActivitySearchParams,
    GeocodeParams,
    GeocodeResult,
    DistanceParams,
    WeatherParams,
    CurrentWeather,
    WeatherForecast,
    CurrencyParams,
    CurrencyConversion,
    APIResponse,
    ErrorResponse,
    GoogleFlightsEmissions,
    AmadeusEmissions,
)


class TestFlightSearchParams:
    """Test FlightSearchParams Pydantic model."""

    def test_valid_flight_params_minimal(self):
        """Test creating FlightSearchParams with minimal required fields."""
        params = FlightSearchParams(
            departure_id="JFK",
            arrival_id="LAX",
            outbound_date="2025-06-15",
        )
        assert params.departure_id == "JFK"
        assert params.arrival_id == "LAX"
        assert params.outbound_date == "2025-06-15"

    def test_valid_flight_params_all_fields(self):
        """Test creating FlightSearchParams with all fields."""
        params = FlightSearchParams(
            departure_id="JFK",
            arrival_id="LAX",
            outbound_date="2025-06-15",
            return_date="2025-06-22",
            trip_type=1,
            adults=2,
            children=1,
            infants_in_seat=0,
            infants_on_lap=1,
            travel_class=2,
            currency="EUR",
            country="gb",
            language="fr",
            max_results=20,
        )
        assert params.trip_type == 1
        assert params.adults == 2
        assert params.currency == "EUR"
        assert params.max_results == 20

    def test_flight_params_default_values(self):
        """Test default values are applied correctly."""
        params = FlightSearchParams(
            departure_id="JFK",
            arrival_id="LAX",
            outbound_date="2025-06-15",
        )
        assert params.trip_type == 1  # Default round trip
        assert params.adults == 1
        assert params.currency == "USD"
        assert params.country == "us"
        assert params.language == "en"
        assert params.max_results == 10
        assert params.children == 0
        assert params.infants_in_seat == 0
        assert params.infants_on_lap == 0

    def test_flight_params_invalid_trip_type(self):
        """Test validation for trip_type range (1-3)."""
        with pytest.raises(ValidationError):
            FlightSearchParams(
                departure_id="JFK",
                arrival_id="LAX",
                outbound_date="2025-06-15",
                trip_type=5,  # Invalid
            )

    def test_flight_params_invalid_travel_class(self):
        """Test validation for travel_class range (1-4)."""
        with pytest.raises(ValidationError):
            FlightSearchParams(
                departure_id="JFK",
                arrival_id="LAX",
                outbound_date="2025-06-15",
                travel_class=5,  # Invalid
            )

    def test_flight_params_invalid_adults(self):
        """Test validation for adults (must be >= 1)."""
        with pytest.raises(ValidationError):
            FlightSearchParams(
                departure_id="JFK",
                arrival_id="LAX",
                outbound_date="2025-06-15",
                adults=0,  # Invalid
            )

    def test_flight_params_invalid_children(self):
        """Test validation for children (must be >= 0)."""
        with pytest.raises(ValidationError):
            FlightSearchParams(
                departure_id="JFK",
                arrival_id="LAX",
                outbound_date="2025-06-15",
                children=-1,  # Invalid
            )


class TestAmadeusFlightSearchParams:
    """Test AmadeusFlightSearchParams Pydantic model."""

    def test_valid_amadeus_flight_params_minimal(self):
        """Test creating AmadeusFlightSearchParams with minimal fields."""
        params = AmadeusFlightSearchParams(
            originLocationCode="JFK",
            destinationLocationCode="LAX",
            departureDate="2025-06-15",
        )
        assert params.originLocationCode == "JFK"
        assert params.destinationLocationCode == "LAX"
        assert params.departureDate == "2025-06-15"

    def test_amadeus_flight_params_default_values(self):
        """Test default values are applied correctly."""
        params = AmadeusFlightSearchParams(
            originLocationCode="JFK",
            destinationLocationCode="LAX",
            departureDate="2025-06-15",
        )
        assert params.adults == 1
        assert params.max == 250

    def test_amadeus_flight_params_adults_range(self):
        """Test adults must be 1-9."""
        with pytest.raises(ValidationError):
            AmadeusFlightSearchParams(
                originLocationCode="JFK",
                destinationLocationCode="LAX",
                departureDate="2025-06-15",
                adults=10,  # Invalid, max is 9
            )

    def test_amadeus_flight_params_children_range(self):
        """Test children must be 0-9."""
        with pytest.raises(ValidationError):
            AmadeusFlightSearchParams(
                originLocationCode="JFK",
                destinationLocationCode="LAX",
                departureDate="2025-06-15",
                children=10,  # Invalid, max is 9
            )

    def test_amadeus_flight_params_optional_fields(self):
        """Test optional fields can be set."""
        params = AmadeusFlightSearchParams(
            originLocationCode="JFK",
            destinationLocationCode="LAX",
            departureDate="2025-06-15",
            returnDate="2025-06-22",
            travelClass="BUSINESS",
            nonStop=True,
            currencyCode="EUR",
            maxPrice=1500,
        )
        assert params.returnDate == "2025-06-22"
        assert params.travelClass == "BUSINESS"
        assert params.nonStop is True
        assert params.currencyCode == "EUR"
        assert params.maxPrice == 1500


class TestHotelSearchParams:
    """Test HotelSearchParams Pydantic model."""

    def test_valid_hotel_params_minimal(self):
        """Test creating HotelSearchParams with minimal fields."""
        params = HotelSearchParams(
            location="Paris",
            check_in_date="2025-06-15",
            check_out_date="2025-06-20",
        )
        assert params.location == "Paris"
        assert params.check_in_date == "2025-06-15"
        assert params.check_out_date == "2025-06-20"

    def test_hotel_params_default_values(self):
        """Test default values are applied correctly."""
        params = HotelSearchParams(
            location="Paris",
            check_in_date="2025-06-15",
            check_out_date="2025-06-20",
        )
        assert params.adults == 2
        assert params.children == 0
        assert params.currency == "USD"
        assert params.country == "us"
        assert params.language == "en"
        assert params.free_cancellation is False
        assert params.special_offers is False
        assert params.vacation_rentals is False
        assert params.max_results == 20

    def test_hotel_params_invalid_adults(self):
        """Test validation for adults (must be >= 1)."""
        with pytest.raises(ValidationError):
            HotelSearchParams(
                location="Paris",
                check_in_date="2025-06-15",
                check_out_date="2025-06-20",
                adults=0,  # Invalid
            )

    def test_hotel_params_invalid_bedrooms(self):
        """Test validation for bedrooms (must be >= 1)."""
        with pytest.raises(ValidationError):
            HotelSearchParams(
                location="Paris",
                check_in_date="2025-06-15",
                check_out_date="2025-06-20",
                bedrooms=0,  # Invalid
            )


class TestEventSearchParams:
    """Test EventSearchParams Pydantic model."""

    def test_valid_event_params_minimal(self):
        """Test creating EventSearchParams with minimal fields."""
        params = EventSearchParams(query="concerts")
        assert params.query == "concerts"

    def test_event_params_default_values(self):
        """Test default values are applied correctly."""
        params = EventSearchParams(query="food festivals")
        assert params.language == "en"
        assert params.country == "us"
        assert params.max_results == 20

    def test_event_params_with_all_fields(self):
        """Test EventSearchParams with all fields."""
        params = EventSearchParams(
            query="theater",
            location="Manhattan NYC",
            date_filter="week",
            event_type="Virtual-Event",
            language="fr",
            country="gb",
            max_results=30,
        )
        assert params.query == "theater"
        assert params.location == "Manhattan NYC"
        assert params.date_filter == "week"
        assert params.language == "fr"
        assert params.max_results == 30


class TestActivitySearchParams:
    """Test ActivitySearchParams Pydantic model."""

    def test_valid_activity_params(self):
        """Test creating ActivitySearchParams with valid coordinates."""
        params = ActivitySearchParams(latitude=40.7128, longitude=-74.0060)
        assert params.latitude == 40.7128
        assert params.longitude == -74.0060

    def test_activity_params_default_radius(self):
        """Test default radius value."""
        params = ActivitySearchParams(latitude=40.7128, longitude=-74.0060)
        assert params.radius == 1
        assert params.radiusUnit == "KM"

    def test_activity_params_invalid_latitude(self):
        """Test validation for latitude range (-90 to 90)."""
        with pytest.raises(ValidationError):
            ActivitySearchParams(latitude=95, longitude=-74.0060)

    def test_activity_params_invalid_longitude(self):
        """Test validation for longitude range (-180 to 180)."""
        with pytest.raises(ValidationError):
            ActivitySearchParams(latitude=40.7128, longitude=185)


class TestGeocodeParams:
    """Test GeocodeParams Pydantic model."""

    def test_valid_geocode_params_minimal(self):
        """Test creating GeocodeParams with minimal fields."""
        params = GeocodeParams(location="Paris, France")
        assert params.location == "Paris, France"

    def test_geocode_params_default_values(self):
        """Test default values are applied correctly."""
        params = GeocodeParams(location="Paris, France")
        assert params.exactly_one is True
        assert params.timeout == 10
        assert params.language == "en"
        assert params.addressdetails is True

    def test_geocode_params_invalid_timeout(self):
        """Test validation for timeout (must be >= 1)."""
        with pytest.raises(ValidationError):
            GeocodeParams(location="Paris", timeout=0)


class TestGeocodeResult:
    """Test GeocodeResult Pydantic model."""

    def test_valid_geocode_result(self):
        """Test creating a valid GeocodeResult."""
        result = GeocodeResult(
            location="Paris",
            latitude=48.8566,
            longitude=2.3522,
            address="Paris, France",
            search_timestamp="2025-01-20T10:30:00Z",
        )
        assert result.location == "Paris"
        assert result.latitude == 48.8566
        assert result.longitude == 2.3522
        assert result.address == "Paris, France"


class TestDistanceParams:
    """Test DistanceParams Pydantic model."""

    def test_valid_distance_params(self):
        """Test creating DistanceParams with valid coordinates."""
        params = DistanceParams(
            lat1=40.7128,
            lon1=-74.0060,
            lat2=51.5074,
            lon2=-0.1278,
        )
        assert params.lat1 == 40.7128
        assert params.lon1 == -74.0060

    def test_distance_params_default_unit(self):
        """Test default unit is kilometers."""
        params = DistanceParams(
            lat1=40.7128,
            lon1=-74.0060,
            lat2=51.5074,
            lon2=-0.1278,
        )
        assert params.unit == "km"

    def test_distance_params_invalid_latitude(self):
        """Test validation for latitude range."""
        with pytest.raises(ValidationError):
            DistanceParams(
                lat1=95,  # Invalid
                lon1=-74.0060,
                lat2=51.5074,
                lon2=-0.1278,
            )


class TestWeatherParams:
    """Test WeatherParams Pydantic model."""

    def test_valid_weather_params(self):
        """Test creating WeatherParams with valid coordinates."""
        params = WeatherParams(latitude=40.7128, longitude=-74.0060)
        assert params.latitude == 40.7128
        assert params.longitude == -74.0060

    def test_weather_params_default_hourly(self):
        """Test default hourly value is False."""
        params = WeatherParams(latitude=40.7128, longitude=-74.0060)
        assert params.hourly is False

    def test_weather_params_hourly_flag(self):
        """Test hourly flag can be set."""
        params = WeatherParams(latitude=40.7128, longitude=-74.0060, hourly=True)
        assert params.hourly is True


class TestCurrentWeather:
    """Test CurrentWeather Pydantic model."""

    def test_valid_current_weather(self):
        """Test creating CurrentWeather with all fields."""
        weather = CurrentWeather(
            timestamp="2025-01-20T10:30:00Z",
            temperature_c=15.5,
            windspeed_kph=10.2,
            winddirection_deg=270.0,
            is_day=True,
            weathercode=0,
        )
        assert weather.temperature_c == 15.5
        assert weather.is_day is True

    def test_current_weather_all_optional(self):
        """Test CurrentWeather with no fields (all optional)."""
        weather = CurrentWeather()
        assert weather.timestamp is None
        assert weather.temperature_c is None


class TestCurrencyParams:
    """Test CurrencyParams Pydantic model."""

    def test_valid_currency_params_minimal(self):
        """Test creating CurrencyParams with minimal fields."""
        params = CurrencyParams(from_currency="USD", to_currency="EUR")
        assert params.from_currency == "USD"
        assert params.to_currency == "EUR"

    def test_currency_params_default_values(self):
        """Test default values are applied correctly."""
        params = CurrencyParams(from_currency="USD", to_currency="EUR")
        assert params.amount == 1.0
        assert params.language == "en"

    def test_currency_params_custom_amount(self):
        """Test custom amount can be set."""
        params = CurrencyParams(
            from_currency="USD",
            to_currency="EUR",
            amount=100.0,
        )
        assert params.amount == 100.0

    def test_currency_params_invalid_amount(self):
        """Test validation for amount (must be > 0)."""
        with pytest.raises(ValidationError):
            CurrencyParams(
                from_currency="USD",
                to_currency="EUR",
                amount=0,  # Invalid
            )


class TestCurrencyConversion:
    """Test CurrencyConversion Pydantic model."""

    def test_valid_currency_conversion(self):
        """Test creating a valid CurrencyConversion."""
        conversion = CurrencyConversion(
            from_currency="USD",
            to_currency="EUR",
            amount=100.0,
            exchange_rate=0.92,
            converted_amount=92.0,
            search_timestamp="2025-01-20T10:30:00Z",
        )
        assert conversion.from_currency == "USD"
        assert conversion.exchange_rate == 0.92
        assert conversion.converted_amount == 92.0


class TestAPIResponse:
    """Test APIResponse Pydantic model."""

    def test_valid_api_response(self):
        """Test creating a valid APIResponse."""
        response = APIResponse(
            provider="SerpAPI",
            search_timestamp="2025-01-20T10:30:00Z",
            data={"flights": [{"price": 299}]},
        )
        assert response.provider == "SerpAPI"
        assert "flights" in response.data


class TestErrorResponse:
    """Test ErrorResponse Pydantic model."""

    def test_valid_error_response(self):
        """Test creating a valid ErrorResponse."""
        error = ErrorResponse(
            error="Flight not found",
            details="No flights available for the given route",
        )
        assert error.error == "Flight not found"
        assert error.details is not None

    def test_error_response_without_details(self):
        """Test ErrorResponse with only error message."""
        error = ErrorResponse(error="Invalid request")
        assert error.error == "Invalid request"
        assert error.details is None


# =====================================================================
# EMISSIONS MODELS TESTS
# =====================================================================


class TestGoogleFlightsEmissions:
    """Test GoogleFlightsEmissions Pydantic model."""

    def test_valid_google_flights_emissions(self):
        """Test creating valid GoogleFlightsEmissions with all fields."""
        emissions = GoogleFlightsEmissions(
            this_flight=81500,
            typical_for_this_route=133000,
            difference_percent=-39,
        )
        assert emissions.this_flight == 81500
        assert emissions.typical_for_this_route == 133000
        assert emissions.difference_percent == -39

    def test_google_flights_emissions_partial(self):
        """Test GoogleFlightsEmissions with partial data."""
        emissions = GoogleFlightsEmissions(
            this_flight=81500,
        )
        assert emissions.this_flight == 81500
        assert emissions.typical_for_this_route is None
        assert emissions.difference_percent is None

    def test_google_flights_emissions_all_none(self):
        """Test GoogleFlightsEmissions with all None values."""
        emissions = GoogleFlightsEmissions()
        assert emissions.this_flight is None
        assert emissions.typical_for_this_route is None
        assert emissions.difference_percent is None

    def test_google_flights_emissions_description(self):
        """Test that GoogleFlightsEmissions fields have descriptions."""
        # Check that model schema has field descriptions
        schema = GoogleFlightsEmissions.model_json_schema()
        assert "properties" in schema
        assert "this_flight" in schema["properties"]
        assert "typical_for_this_route" in schema["properties"]
        assert "difference_percent" in schema["properties"]


class TestAmadeusEmissions:
    """Test AmadeusEmissions Pydantic model."""

    def test_valid_amadeus_emissions_economy(self):
        """Test creating valid AmadeusEmissions for economy cabin."""
        emissions = AmadeusEmissions(
            weight=90.39,
            weightUnit="KG",
            cabin="ECONOMY",
        )
        assert emissions.weight == 90.39
        assert emissions.weightUnit == "KG"
        assert emissions.cabin == "ECONOMY"

    def test_valid_amadeus_emissions_business(self):
        """Test creating AmadeusEmissions for business cabin."""
        emissions = AmadeusEmissions(
            weight=180.78,
            weightUnit="KG",
            cabin="BUSINESS",
        )
        assert emissions.weight == 180.78
        assert emissions.cabin == "BUSINESS"

    def test_amadeus_emissions_without_cabin(self):
        """Test AmadeusEmissions without cabin specification."""
        emissions = AmadeusEmissions(
            weight=90.39,
            weightUnit="KG",
        )
        assert emissions.weight == 90.39
        assert emissions.cabin is None

    def test_amadeus_emissions_zero_weight(self):
        """Test AmadeusEmissions with zero weight (edge case)."""
        emissions = AmadeusEmissions(
            weight=0.0,
            weightUnit="KG",
        )
        assert emissions.weight == 0.0

    def test_amadeus_emissions_large_weight(self):
        """Test AmadeusEmissions with large weight values."""
        emissions = AmadeusEmissions(
            weight=1500.5,
            weightUnit="KG",
            cabin="FIRST",
        )
        assert emissions.weight == 1500.5
        assert emissions.cabin == "FIRST"

    def test_amadeus_emissions_description(self):
        """Test that AmadeusEmissions fields have descriptions."""
        schema = AmadeusEmissions.model_json_schema()
        assert "properties" in schema
        assert "weight" in schema["properties"]
        assert "weightUnit" in schema["properties"]
        assert "cabin" in schema["properties"]


class TestAmadeusHotelOfferParams:
    """Test AmadeusHotelOfferParams Pydantic model."""

    def test_valid_amadeus_hotel_offer_params(self):
        """Test creating AmadeusHotelOfferParams with valid fields."""
        params = AmadeusHotelOfferParams(
            cityCode="PAR",
            checkInDate="2025-06-15",
            checkOutDate="2025-06-20",
            adults=2,
        )
        assert params.cityCode == "PAR"
        assert params.adults == 2

    def test_amadeus_hotel_offer_params_default_adults(self):
        """Test default adults value is 1."""
        params = AmadeusHotelOfferParams()
        assert params.adults == 1

    def test_amadeus_hotel_offer_params_all_optional(self):
        """Test all fields are optional."""
        params = AmadeusHotelOfferParams()
        assert params.cityCode is None
        assert params.hotelIds is None
