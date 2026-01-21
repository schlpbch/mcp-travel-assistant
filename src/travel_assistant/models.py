"""Data models for the Travel Assistant MCP server."""

from dataclasses import dataclass
from typing import Any

from amadeus import Client
from pydantic import BaseModel, Field, field_validator

from travel_assistant.helpers import validate_currency_code, validate_date_format

# Re-export accessibility models
from mcp_accessibility_models import (  # noqa: F401
    AccessibilityRequest,
    FlightAccessibility,
    HotelAccessibility,
)

# =====================================================================
# APPLICATION CONTEXT
# =====================================================================


@dataclass
class AppContext:
    """Application context containing shared resources."""

    amadeus_client: Client


# =====================================================================
# FLIGHT SEARCH MODELS
# =====================================================================


class FlightSearchParams(BaseModel):
    """Parameters for flight search via SerpAPI."""

    departure_id: str = Field(
        ..., description="Departure airport code or city (e.g., 'DEL', 'JFK')"
    )
    arrival_id: str = Field(
        ..., description="Arrival airport code or city (e.g., 'CDG', 'LHR')"
    )
    outbound_date: str = Field(..., description="Outbound date in YYYY-MM-DD format")
    return_date: str | None = Field(
        None, description="Return date in YYYY-MM-DD format (optional for one-way)"
    )
    trip_type: int = Field(
        1, ge=1, le=3, description="Trip type (1=Round trip, 2=One way, 3=Multi-city)"
    )
    adults: int = Field(1, ge=1, description="Number of adult travelers (18+)")
    children: int = Field(0, ge=0, description="Number of children (2-11 years)")
    infants_in_seat: int = Field(
        0, ge=0, description="Number of infants with own seat (under 2)"
    )
    infants_on_lap: int = Field(0, ge=0, description="Number of lap infants (under 2)")
    travel_class: int = Field(
        1,
        ge=1,
        le=4,
        description="Travel class (1=Economy, 2=Premium Economy, 3=Business, 4=First)",
    )
    currency: str = Field("USD", description="Currency code (e.g., 'USD', 'EUR')")
    country: str = Field(
        "us", description="Country code for localized results (e.g., 'us', 'gb')"
    )
    language: str = Field("en", description="Language code (e.g., 'en', 'fr')")
    max_results: int = Field(
        10, ge=1, le=50, description="Maximum number of results to return"
    )

    @field_validator("outbound_date", "return_date")
    @classmethod
    def validate_dates(cls, v):
        if v:
            return validate_date_format(v)
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v):
        return validate_currency_code(v)


class AmadeusFlightSearchParams(BaseModel):
    """Parameters for flight search via Amadeus GDS."""

    originLocationCode: str = Field(
        ..., description="IATA code of origin city/airport (e.g., 'SYD')"
    )
    destinationLocationCode: str = Field(
        ..., description="IATA code of destination city/airport (e.g., 'BKK')"
    )
    departureDate: str = Field(..., description="Departure date in YYYY-MM-DD format")
    adults: int = Field(
        1, ge=1, le=9, description="Number of adult travelers (age 12+)"
    )
    returnDate: str | None = Field(
        None, description="Return date in YYYY-MM-DD format (optional)"
    )
    children: int | None = Field(
        None, ge=0, le=9, description="Number of children (age 2-11)"
    )
    infants: int | None = Field(None, ge=0, description="Number of infants (age <= 2)")
    travelClass: str | None = Field(
        None, description="Travel class (ECONOMY, PREMIUM_ECONOMY, BUSINESS, FIRST)"
    )
    includedAirlineCodes: str | None = Field(
        None, description="Comma-separated airline codes to include"
    )
    excludedAirlineCodes: str | None = Field(
        None, description="Comma-separated airline codes to exclude"
    )
    nonStop: bool | None = Field(None, description="Filter for non-stop flights only")
    currencyCode: str | None = Field(None, description="ISO 4217 currency code")
    maxPrice: int | None = Field(None, ge=0, description="Maximum price per traveler")
    max: int = Field(
        250, ge=1, le=250, description="Maximum number of results to return"
    )


# =====================================================================
# HOTEL SEARCH MODELS
# =====================================================================


class HotelSearchParams(BaseModel):
    """Parameters for hotel search via SerpAPI."""

    location: str = Field(
        ...,
        description="Destination location (e.g., 'Paris city center', 'Tokyo Shibuya')",
    )
    check_in_date: str = Field(..., description="Check-in date in YYYY-MM-DD format")
    check_out_date: str = Field(..., description="Check-out date in YYYY-MM-DD format")
    adults: int = Field(2, ge=1, description="Number of adult guests")
    children: int = Field(0, ge=0, description="Number of children")
    children_ages: list[int] | None = Field(
        None, description="Ages of children for room configuration"
    )
    currency: str = Field("USD", description="Currency code for pricing")
    country: str = Field("us", description="Country code for localized results")
    language: str = Field("en", description="Language code for results")
    sort_by: int | None = Field(
        None, description="Sort order (3=Best deals, 8=Highest rated, 13=Most popular)"
    )
    hotel_class: list[int] | None = Field(
        None, description="Star ratings to filter (e.g., [4, 5])"
    )
    amenities: list[int] | None = Field(None, description="Required amenities filter")
    property_types: list[int] | None = Field(None, description="Property type filter")
    brands: list[int] | None = Field(None, description="Hotel brand filter")
    free_cancellation: bool = Field(
        False, description="Show only free cancellation options"
    )
    special_offers: bool = Field(False, description="Show only special offers")
    vacation_rentals: bool = Field(
        False, description="Include vacation rentals in search"
    )
    bedrooms: int | None = Field(None, ge=1, description="Minimum number of bedrooms")
    max_results: int = Field(20, ge=1, le=50, description="Maximum number of results")


class AmadeusHotelOfferParams(BaseModel):
    """Parameters for Amadeus hotel offer search."""

    cityCode: str | None = Field(
        None, description="IATA code of city (e.g., 'PAR' for Paris)"
    )
    hotelIds: str | None = Field(None, description="Comma-separated list of hotel IDs")
    checkInDate: str | None = Field(
        None, description="Check-in date in YYYY-MM-DD format"
    )
    checkOutDate: str | None = Field(
        None, description="Check-out date in YYYY-MM-DD format"
    )
    adults: int = Field(1, ge=1, description="Number of adult guests")
    roomQuantity: int | None = Field(
        None, ge=1, description="Number of rooms requested"
    )
    priceRange: str | None = Field(
        None, description="Price range filter (e.g., '50-200')"
    )
    currency: str | None = Field(None, description="Currency code for prices")
    paymentPolicy: str | None = Field(
        None, description="Payment policy (GUARANTEE, DEPOSIT, NONE)"
    )
    boardType: str | None = Field(
        None, description="Board type (ROOM_ONLY, BREAKFAST, HALF_BOARD, FULL_BOARD)"
    )
    includeClosed: bool | None = Field(
        None, description="Include temporarily closed hotels"
    )
    bestRateOnly: bool | None = Field(
        None, description="Return only best rate per hotel"
    )
    view: str | None = Field(None, description="Response view (FULL, LIGHT)")
    sort: str | None = Field(None, description="Sort order (PRICE, NONE)")
    lang: str | None = Field(None, description="Language code for descriptions")


# =====================================================================
# EVENT & ACTIVITY SEARCH MODELS
# =====================================================================


class EventSearchParams(BaseModel):
    """Parameters for event search via SerpAPI."""

    query: str = Field(
        ..., description="Search query (e.g., 'concerts', 'food festivals', 'theater')"
    )
    location: str | None = Field(
        None, description="Location filter (e.g., 'Manhattan NYC', 'Paris Marais')"
    )
    date_filter: str | None = Field(
        None,
        description="Date filter (today, tomorrow, week, weekend, next_week, month, next_month)",
    )
    event_type: str | None = Field(
        None, description="Event type filter (e.g., 'Virtual-Event')"
    )
    language: str = Field("en", description="Language code for results")
    country: str = Field("us", description="Country code for localized results")
    max_results: int = Field(20, ge=1, le=50, description="Maximum number of results")


class ActivitySearchParams(BaseModel):
    """Parameters for activity/tour search via Amadeus."""

    latitude: float = Field(..., ge=-90, le=90, description="Latitude of location")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude of location")
    radius: int | None = Field(1, ge=0, description="Search radius (default: 1 km)")
    radiusUnit: str = Field(
        "KM", description="Radius unit ('KM' for kilometers, 'MI' for miles)"
    )


# =====================================================================
# GEOCODING MODELS
# =====================================================================


class GeocodeParams(BaseModel):
    """Parameters for geocoding location to coordinates."""

    location: str = Field(..., description="Location name, address, or landmark")
    exactly_one: bool = Field(
        True, description="Return best match only vs. multiple options"
    )
    timeout: int = Field(10, ge=1, description="Timeout in seconds")
    language: str = Field("en", description="Language code for results")
    addressdetails: bool = Field(
        True, description="Include detailed address information"
    )
    country_codes: str | None = Field(
        None, description="Limit search to specific countries (comma-separated)"
    )


class GeocodeResult(BaseModel):
    """Result of geocoding a location."""

    location: str
    latitude: float
    longitude: float
    address: str
    search_timestamp: str


class DistanceParams(BaseModel):
    """Parameters for distance calculation."""

    lat1: float = Field(..., ge=-90, le=90, description="Latitude of first location")
    lon1: float = Field(..., ge=-180, le=180, description="Longitude of first location")
    lat2: float = Field(..., ge=-90, le=90, description="Latitude of second location")
    lon2: float = Field(
        ..., ge=-180, le=180, description="Longitude of second location"
    )
    unit: str = Field("km", description="Distance unit ('km', 'miles', 'nm')")


# =====================================================================
# WEATHER MODELS
# =====================================================================


class WeatherParams(BaseModel):
    """Parameters for weather forecast."""

    latitude: float = Field(..., ge=-90, le=90, description="Latitude of location")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude of location")
    hourly: bool = Field(False, description="Request hourly forecast (vs. daily)")


class CurrentWeather(BaseModel):
    """Current weather conditions."""

    timestamp: str | None = None
    temperature_c: float | None = None
    windspeed_kph: float | None = None
    winddirection_deg: float | None = None
    is_day: bool | None = None
    weathercode: int | None = None


class WeatherForecast(BaseModel):
    """Weather forecast data."""

    coordinates: dict[str, float]
    provider: str
    forecast_type: str
    forecast_periods: list[dict[str, Any]]
    forecast_metadata: dict[str, Any]
    search_timestamp: str


# =====================================================================
# CURRENCY MODELS
# =====================================================================


class CurrencyParams(BaseModel):
    """Parameters for currency conversion."""

    from_currency: str = Field(..., description="Source currency code (e.g., 'USD')")
    to_currency: str = Field(..., description="Target currency code (e.g., 'EUR')")
    amount: float = Field(1.0, gt=0, description="Amount to convert")
    language: str = Field("en", description="Language code")


class CurrencyConversion(BaseModel):
    """Currency conversion result."""

    from_currency: str
    to_currency: str
    amount: float
    exchange_rate: float
    converted_amount: float
    search_timestamp: str


# =====================================================================
# API RESPONSE MODELS
# =====================================================================


class APIResponse(BaseModel):
    """Generic API response wrapper."""

    provider: str
    search_timestamp: str
    data: dict[str, Any]


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str
    details: str | None = None


# =====================================================================
# EMISSIONS MODELS
# =====================================================================


class GoogleFlightsEmissions(BaseModel):
    """Carbon emissions data from Google Flights (SerpAPI)."""

    this_flight: int | None = Field(
        None, description="CO2 emissions for this flight in grams"
    )
    typical_for_this_route: int | None = Field(
        None, description="Typical CO2 emissions for this route in grams"
    )
    difference_percent: int | None = Field(
        None, description="Percentage difference vs typical (negative = better)"
    )


class AmadeusEmissions(BaseModel):
    """Carbon emissions data from Amadeus GDS."""

    weight: float = Field(..., description="CO2 emissions weight")
    weightUnit: str = Field(..., description="Unit of weight (e.g., 'KG')")
    cabin: str | None = Field(
        None,
        description="Cabin class this emissions applies to (e.g., 'ECONOMY', 'BUSINESS')",
    )
