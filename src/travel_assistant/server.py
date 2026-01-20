import os
import json
import requests
from typing import List, Dict, Optional, Any
from datetime import datetime
from dataclasses import dataclass
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from dotenv import load_dotenv
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable

from amadeus import Client, ResponseError
from fastmcp import FastMCP, Context

from travel_assistant.clients import SerpAPIClient
from travel_assistant.helpers import (
    get_serpapi_key,
    get_exchange_rate_api_key,
    get_geolocator,
    get_nws_headers,
    make_nws_request,
    format_amadeus_response,
    format_error_response,
    build_optional_params,
    extract_hotel_accessibility,
    extract_amadeus_hotel_accessibility,
    extract_flight_accessibility_from_amadeus,
)

load_dotenv()

# =====================================================================
# APPLICATION CONTEXT AND LIFECYCLE
# =====================================================================

@dataclass
class AppContext:
    amadeus_client: Client

@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Manage Amadeus client lifecycle"""
    api_key = os.environ.get("AMADEUS_API_KEY")
    api_secret = os.environ.get("AMADEUS_API_SECRET")

    amadeus_client = None
    if api_key and api_secret:
        try:
            amadeus_client = Client(
                client_id=api_key,
                client_secret=api_secret
            )
        except Exception as e:
            # Log but don't fail startup - Amadeus tools will handle missing client gracefully
            pass

    try:
        yield AppContext(amadeus_client=amadeus_client)
    finally:
        pass

# Initialize FastMCP server with lifespan
mcp = FastMCP("Travel Concierge", lifespan=app_lifespan)

# Add health check endpoint
@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    """Health check endpoint for monitoring and load balancers."""
    return {
        "status": "healthy",
        "service": "Travel Concierge",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

# Initialize API clients (created once per server instance)
serpapi_client = SerpAPIClient()

# =====================================================================
# COMBINED FLIGHT SEARCH TOOLS
# =====================================================================

@mcp.tool()
def search_flights_serpapi(
    departure_id: str,
    arrival_id: str,
    outbound_date: str,
    return_date: Optional[str] = None,
    trip_type: int = 1,
    adults: int = 1,
    children: int = 0,
    infants_in_seat: int = 0,
    infants_on_lap: int = 0,
    travel_class: int = 1,
    currency: str = "USD",
    country: str = "us",
    language: str = "en",
    max_results: int = 10
) -> Dict[str, Any]:
    """Searches Google Flights for best deals and routes with carbon emissions data. Takes departure location, arrival destination, outbound date, optional return date, passenger counts by type (adults, children, infants), seat class, currency, language, and max results. Returns curated flight options with prices, schedules, airline booking links, and CO2 emissions per flight ranked by value."""

    try:
        # Build search parameters (client adds engine and api_key)
        params = {
            "departure_id": departure_id,
            "arrival_id": arrival_id,
            "outbound_date": outbound_date,
            "type": trip_type,
            "adults": adults,
            "children": children,
            "infants_in_seat": infants_in_seat,
            "infants_on_lap": infants_on_lap,
            "travel_class": travel_class,
            "currency": currency,
            "hl": language,
            "gl": country,
            "emissions": 1,  # Request emissions data from SerpAPI
        }

        if return_date and trip_type == 1:  # Round trip
            params["return_date"] = return_date

        # Make API request (client handles engine, api_key, timeout)
        flight_data = serpapi_client.search_flights(**params)

        # Extract and process emissions data from flights
        def extract_emissions(flights):
            """Extract carbon emissions data from flight list."""
            processed_flights = []
            for flight in flights:
                flight_copy = flight.copy()
                # Extract carbon_emissions if present
                if "carbon_emissions" in flight:
                    emissions = flight.get("carbon_emissions", {})
                    flight_copy["carbon_emissions"] = {
                        "this_flight_grams": emissions.get("this_flight"),
                        "typical_for_route_grams": emissions.get("typical_for_this_route"),
                        "difference_percent": emissions.get("difference_percent"),
                        "note": "Negative difference % indicates lower emissions than typical for this route"
                    }
                processed_flights.append(flight_copy)
            return processed_flights

        # Process flight results
        processed_results = {
            "provider": "Google Flights (SerpAPI)",
            "search_metadata": {
                "departure": departure_id,
                "arrival": arrival_id,
                "outbound_date": outbound_date,
                "return_date": return_date,
                "trip_type": "Round trip" if trip_type == 1 else "One way" if trip_type == 2 else "Multi-city",
                "passengers": {
                    "adults": adults,
                    "children": children,
                    "infants_in_seat": infants_in_seat,
                    "infants_on_lap": infants_on_lap
                },
                "travel_class": ["Economy", "Premium economy", "Business", "First"][travel_class - 1],
                "currency": currency,
                "emissions_included": True,
                "accessibility_note": "For accessibility requirements (wheelchair, deaf, blind, stretcher), contact airlines directly with IATA Special Service Request (SSR) codes: WCHR (wheelchair), WCHS (wheelchair with stowage), STCR (stretcher), DEAF, BLND, PRMK (mobility disability)",
                "search_timestamp": datetime.now().isoformat()
            },
            "best_flights": extract_emissions(flight_data.get("best_flights", [])[:max_results]),
            "other_flights": extract_emissions(flight_data.get("other_flights", [])[:max_results]),
            "price_insights": flight_data.get("price_insights", {}),
            "airports": flight_data.get("airports", [])
        }

        return processed_results

    except ValueError as e:
        return format_error_response(str(e))
    except Exception as e:
        return format_error_response(f"Google Flights API error: {str(e)}")

@mcp.tool()
def search_flights_amadeus(
    originLocationCode: str,
    destinationLocationCode: str,
    departureDate: str,
    adults: int,
    ctx: Context,
    returnDate: str = None,
    children: int = None,
    infants: int = None,
    travelClass: str = None,
    includedAirlineCodes: str = None,
    excludedAirlineCodes: str = None,
    nonStop: bool = None,
    currencyCode: str = None,
    maxPrice: int = None,
    max: int = 250
) -> str:
    """Searches Amadeus Global Distribution System for professional flight offers with carbon emissions data. Takes departure/arrival airport codes (IATA), travel dates, passenger counts, seat classes, airline filters, and optional preferences. Returns curated flight options with pricing, schedules, seat availability, booking confirmation numbers, and per-cabin CO2 emissions."""
    if adults and not (1 <= adults <= 9):
        return format_error_response("Adults must be between 1 and 9")

    if children and infants and adults and (adults + children > 9):
        return format_error_response("Total number of seated travelers (adults + children) cannot exceed 9")

    if infants and adults and (infants > adults):
        return format_error_response("Number of infants cannot exceed number of adults")

    amadeus_client = ctx.request_context.lifespan_context.amadeus_client
    params = build_optional_params(
        required_params={
            "originLocationCode": originLocationCode,
            "destinationLocationCode": destinationLocationCode,
            "departureDate": departureDate,
            "adults": adults,
        },
        optional_params={
            "returnDate": returnDate,
            "children": children,
            "infants": infants,
            "travelClass": travelClass,
            "includedAirlineCodes": includedAirlineCodes,
            "excludedAirlineCodes": excludedAirlineCodes,
            "nonStop": nonStop,
            "currencyCode": currencyCode,
            "maxPrice": maxPrice,
            "max": max,
        },
        none_check_fields={"children", "infants", "nonStop", "maxPrice", "max"},
    )

    try:
        ctx.info(f"Searching Amadeus flights from {originLocationCode} to {destinationLocationCode}")
        ctx.info(f"API parameters: {json.dumps(params)}")

        response = amadeus_client.shopping.flight_offers_search.get(**params)
        result = response.body

        # Process emissions and accessibility data from flight offers
        if "data" in result and isinstance(result["data"], list):
            for flight_offer in result["data"]:
                # Extract and format co2Emissions if present
                if "co2Emissions" in flight_offer:
                    emissions_array = flight_offer.get("co2Emissions", [])
                    flight_offer["co2_emissions_summary"] = {
                        "emissions_by_cabin": [
                            {
                                "cabin": emission.get("cabin", "UNKNOWN"),
                                "weight_kg": emission.get("weight"),
                                "per_passenger_kg": round(emission.get("weight", 0) / (adults or 1), 2)
                            }
                            for emission in emissions_array
                        ],
                        "total_weight_kg": sum(e.get("weight", 0) for e in emissions_array),
                        "unit": "kilograms"
                    }

                # Extract accessibility information
                flight_offer["accessibility"] = extract_flight_accessibility_from_amadeus(flight_offer)

        result["provider"] = "Amadeus GDS"
        result["emissions_included"] = bool("co2Emissions" in result.get("data", [{}])[0] if result.get("data") else False)
        result["accessibility_included"] = True
        result["search_timestamp"] = datetime.now().isoformat()
        return json.dumps(result)
    except ResponseError as error:
        error_msg = f"Amadeus API error: {str(error)}"
        ctx.info(f"Error: {error_msg}")
        return format_error_response(error_msg)
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        ctx.info(f"Error: {error_msg}")
        return format_error_response(error_msg)

# =====================================================================
# COMBINED HOTEL SEARCH TOOLS
# =====================================================================

@mcp.tool()
def search_hotels_serpapi(
    location: str,
    check_in_date: str,
    check_out_date: str,
    adults: int = 2,
    children: int = 0,
    children_ages: Optional[List[int]] = None,
    currency: str = "USD",
    country: str = "us",
    language: str = "en",
    sort_by: Optional[int] = None,
    hotel_class: Optional[List[int]] = None,
    amenities: Optional[List[int]] = None,
    property_types: Optional[List[int]] = None,
    brands: Optional[List[int]] = None,
    free_cancellation: bool = False,
    special_offers: bool = False,
    vacation_rentals: bool = False,
    bedrooms: Optional[int] = None,
    max_results: int = 20
) -> Dict[str, Any]:
    """Searches Google Hotels for accommodations including hotels, vacation rentals, and boutiques. Takes destination, check-in/out dates, guest count, optional filters (star rating, amenities, brands, property types, free cancellation, special offers). Returns available options with prices, ratings, reviews, photos, and direct booking links."""
    
    try:
        # Build search parameters (client adds engine and api_key)
        params = {
            "q": location,
            "check_in_date": check_in_date,
            "check_out_date": check_out_date,
            "adults": adults,
            "children": children,
            "currency": currency,
            "gl": country,
            "hl": language,
        }

        # Add optional parameters
        if children_ages:
            params["children_ages"] = ",".join(map(str, children_ages))
        if sort_by:
            params["sort_by"] = sort_by
        if hotel_class:
            params["hotel_class"] = ",".join(map(str, hotel_class))
        if amenities:
            params["amenities"] = ",".join(map(str, amenities))
        if property_types:
            params["property_types"] = ",".join(map(str, property_types))
        if brands:
            params["brands"] = ",".join(map(str, brands))
        if free_cancellation:
            params["free_cancellation"] = "true"
        if special_offers:
            params["special_offers"] = "true"
        if vacation_rentals:
            params["vacation_rentals"] = "true"
        if bedrooms:
            params["bedrooms"] = bedrooms

        # Make API request (client handles engine, api_key, timeout)
        hotel_data = serpapi_client.search_hotels(**params)
        
        # Process hotel results with accessibility extraction
        properties = hotel_data.get("properties", [])[:max_results]

        # Extract accessibility information for each property
        for prop in properties:
            prop["accessibility"] = extract_hotel_accessibility(prop)

        processed_results = {
            "provider": "Google Hotels (SerpAPI)",
            "search_metadata": {
                "location": location,
                "check_in_date": check_in_date,
                "check_out_date": check_out_date,
                "guests": {
                    "adults": adults,
                    "children": children,
                    "children_ages": children_ages or []
                },
                "currency": currency,
                "search_timestamp": datetime.now().isoformat()
            },
            "properties": properties,
            "filters": hotel_data.get("filters", {}),
            "search_parameters": hotel_data.get("search_parameters", {}),
            "location_info": hotel_data.get("place_results", {}),
            "accessibility_included": True
        }

        return processed_results

    except ValueError as e:
        return format_error_response(str(e))
    except Exception as e:
        return format_error_response(f"Google Hotels API error: {str(e)}")

@mcp.tool()
def search_hotels_amadeus_by_city(
    cityCode: str,
    ctx: Context,
    radius: int = None,
    radiusUnit: str = None,
    chainCodes: str = None,
    amenities: str = None,
    ratings: str = None,
    hotelSource: str = None
) -> str:
    """Searches Amadeus professional hotel inventory by city IATA code. Takes city code, optional search radius (KM/MI), hotel chain codes, amenities (WiFi, Spa, Pool, etc.), star ratings (1-5), and content source. Returns professional rates, room inventory, cancellation policies, and availability. Use for business travel and professional bookings."""
    amadeus_client = ctx.request_context.lifespan_context.amadeus_client
    params = build_optional_params(
        required_params={"cityCode": cityCode},
        optional_params={
            "radius": radius,
            "radiusUnit": radiusUnit,
            "chainCodes": chainCodes,
            "amenities": amenities,
            "ratings": ratings,
            "hotelSource": hotelSource,
        },
        none_check_fields={"radius"},
    )

    try:
        ctx.info(f"Searching Amadeus hotels in city: {cityCode}")
        ctx.info(f"API parameters: {json.dumps(params)}")

        response = amadeus_client.reference_data.locations.hotels.by_city.get(**params)
        return format_amadeus_response(response.body)
    except ResponseError as error:
        error_msg = f"Amadeus API error: {str(error)}"
        ctx.info(f"Error: {error_msg}")
        return format_error_response(error_msg)
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        ctx.info(f"Error: {error_msg}")
        return format_error_response(error_msg)

@mcp.tool()
def search_hotels_amadeus_geocode(
    latitude: float,
    longitude: float,
    ctx: Context,
    radius: int = None,
    radiusUnit: str = None,
    chainCodes: str = None,
    amenities: str = None,
    ratings: str = None,
    hotelSource: str = None
) -> str:
    """Searches for hotels near specific coordinates using Amadeus API. Takes latitude, longitude, optional search radius with unit (KM or MI), hotel chain filters, amenity requirements (e.g., SPA, WIFI, POOL), star ratings (1-5), and content source. Returns available hotels sorted by distance with rates, amenities, and booking links."""
    amadeus_client = ctx.request_context.lifespan_context.amadeus_client
    params = build_optional_params(
        required_params={"latitude": latitude, "longitude": longitude},
        optional_params={
            "radius": radius,
            "radiusUnit": radiusUnit,
            "chainCodes": chainCodes,
            "amenities": amenities,
            "ratings": ratings,
            "hotelSource": hotelSource,
        },
        none_check_fields={"radius"},
    )

    try:
        ctx.info(f"Searching Amadeus hotels at coordinates: {latitude}, {longitude}")
        ctx.info(f"API parameters: {json.dumps(params)}")
        
        response = amadeus_client.reference_data.locations.hotels.by_geocode.get(**params)
        return format_amadeus_response(response.body)
    except ResponseError as error:
        error_msg = f"Amadeus API error: {str(error)}"
        ctx.info(f"Error: {error_msg}")
        return format_error_response(error_msg)
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        ctx.info(f"Error: {error_msg}")
        return format_error_response(error_msg)

@mcp.tool()
def search_hotel_offers_amadeus(
    ctx: Context,
    cityCode: str = None,
    hotelIds: str = None,
    checkInDate: str = None,
    checkOutDate: str = None,
    adults: int = 1,
    roomQuantity: int = None,
    priceRange: str = None,
    currency: str = None,
    paymentPolicy: str = None,
    boardType: str = None,
    includeClosed: bool = None,
    bestRateOnly: bool = None,
    view: str = None,
    sort: str = None,
    lang: str = None
) -> str:
    """Retrieves real-time hotel booking offers from Amadeus. Takes city code or hotel IDs, check-in/out dates, guest count, optional filters (price range, board type, payment policy), currency, and sorting. Returns available room offers with rates, meal plans, and cancellation policies."""
    if not cityCode and not hotelIds:
        return format_error_response("Either cityCode or hotelIds must be provided")

    amadeus_client = ctx.request_context.lifespan_context.amadeus_client
    params = build_optional_params(
        required_params={"adults": adults},
        optional_params={
            "cityCode": cityCode,
            "hotelIds": hotelIds,
            "checkInDate": checkInDate,
            "checkOutDate": checkOutDate,
            "roomQuantity": roomQuantity,
            "priceRange": priceRange,
            "currency": currency,
            "paymentPolicy": paymentPolicy,
            "boardType": boardType,
            "includeClosed": includeClosed,
            "bestRateOnly": bestRateOnly,
            "view": view,
            "sort": sort,
            "lang": lang,
        },
        none_check_fields={"roomQuantity", "includeClosed", "bestRateOnly"},
    )

    try:
        search_location = cityCode if cityCode else f"hotels {hotelIds}"
        ctx.info(f"Searching Amadeus hotel offers for: {search_location}")
        ctx.info(f"API parameters: {json.dumps(params)}")

        response = amadeus_client.shopping.hotel_offers.get(**params)
        return format_amadeus_response(response.body)
    except ResponseError as error:
        error_msg = f"Amadeus API error: {str(error)}"
        ctx.info(f"Error: {error_msg}")
        return format_error_response(error_msg)
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        ctx.info(f"Error: {error_msg}")
        return format_error_response(error_msg)

# =====================================================================
# COMBINED ACTIVITY & EVENT SEARCH TOOLS
# =====================================================================

@mcp.tool()
def search_events_serpapi(
    query: str,
    location: Optional[str] = None,
    date_filter: Optional[str] = None,
    event_type: Optional[str] = None,
    language: str = "en",
    country: str = "us",
    max_results: int = 20
) -> Dict[str, Any]:
    """Searches Google Events for local festivals, shows, and experiences. Takes search query (e.g., concerts, festivals), location, optional date filter, event type, language, and country. Returns curated events with dates, times, locations, descriptions, and booking information."""
    
    try:
        # Build search query
        search_query = query
        if location:
            search_query += f" in {location}"

        # Build search parameters (client adds engine and api_key)
        params = {
            "q": search_query,
            "hl": language,
            "gl": country,
        }

        # Add optional filters
        if date_filter:
            params["htichips"] = f"date:{date_filter}"
        if event_type:
            params["htichips"] = f"event_type:{event_type}"

        # Make API request (client handles engine, api_key, timeout)
        event_data = serpapi_client.search_events(**params)
        
        # Process event results
        processed_results = {
            "provider": "Google Events (SerpAPI)",
            "search_metadata": {
                "query": query,
                "location": location,
                "date_filter": date_filter,
                "event_type": event_type,
                "language": language,
                "country": country,
                "search_timestamp": datetime.now().isoformat()
            },
            "events": event_data.get("events_results", [])[:max_results],
            "search_parameters": event_data.get("search_parameters", {})
        }
        
        return processed_results

    except ValueError as e:
        return format_error_response(str(e))
    except Exception as e:
        return format_error_response(f"Google Events API error: {str(e)}")

@mcp.tool()
def search_activities_amadeus(
    latitude: float,
    longitude: float,
    ctx: Context,
    radius: int = None,
    radiusUnit: str = "KM"
) -> str:
    """Searches Amadeus professional activities and tours by geographic coordinates. Takes latitude, longitude, optional search radius (KM default), returns curated tours and experiences with descriptions, pricing, duration, age/health requirements, cancellation policies, and user ratings. Use for activity planning and booking verified tour operators."""
    amadeus_client = ctx.request_context.lifespan_context.amadeus_client
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "radius": radius or 1,
        "radiusUnit": radiusUnit
    }
    
    try:
        ctx.info(f"Searching Amadeus tours and activities at coordinates: {latitude}, {longitude}")
        ctx.info(f"API parameters: {json.dumps(params)}")

        # Note: This endpoint might be available in newer versions of the Amadeus SDK
        response = amadeus_client.shopping.activities.get(**params)
        return format_amadeus_response(response.body)
    except ResponseError as error:
        error_msg = f"Amadeus API error: {str(error)}"
        ctx.info(f"Error: {error_msg}")
        return format_error_response(error_msg)
    except AttributeError as e:
        error_msg = f"Tours and Activities API not available in current SDK version: {str(e)}"
        ctx.info(f"Error: {error_msg}")
        return format_error_response(error_msg + " (This API might require a newer SDK version or special access)")
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        ctx.info(f"Error: {error_msg}")
        return format_error_response(error_msg)

@mcp.tool()
def get_activity_details_amadeus(
    activityId: str,
    ctx: Context
) -> str:
    """Retrieves complete activity details from Amadeus. Takes activity ID and returns full information including schedules, pricing, age/health requirements, cancellation policies, and direct booking links."""
    amadeus_client = ctx.request_context.lifespan_context.amadeus_client
    
    try:
        ctx.info(f"Getting Amadeus activity details for: {activityId}")

        response = amadeus_client.shopping.activity(activityId).get()
        return format_amadeus_response(response.body)
    except ResponseError as error:
        error_msg = f"Amadeus API error: {str(error)}"
        ctx.info(f"Error: {error_msg}")
        return format_error_response(error_msg)
    except AttributeError as e:
        error_msg = f"Tours and Activities API not available in current SDK version: {str(e)}"
        ctx.info(f"Error: {error_msg}")
        return format_error_response(error_msg + " (This API might require a newer SDK version or special access)")
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        ctx.info(f"Error: {error_msg}")
        return format_error_response(error_msg)

# =====================================================================
# GEOCODING TOOLS
# =====================================================================

@mcp.tool()
def geocode_location(
    location: str,
    exactly_one: bool = True,
    timeout: int = 10,
    language: str = "en",
    addressdetails: bool = True,
    country_codes: Optional[str] = None
) -> Dict[str, Any]:
    """Converts place names and addresses to precise geographic coordinates. Takes location query, optional language preference, country filtering (country codes), and match count preference. Returns latitude/longitude, full address details, timezone info, and disambiguation data. Use for flight/hotel searches, activity mapping, and route planning."""
    
    try:
        geocode, _ = get_geolocator()
        
        # Build geocoding parameters
        geocode_params = {
            "exactly_one": exactly_one,
            "timeout": timeout,
            "language": language,
            "addressdetails": addressdetails
        }
        
        if country_codes:
            geocode_params["country_codes"] = country_codes.split(",")
        
        # Perform geocoding
        result = geocode(location, **geocode_params)
        
        if not result:
            return {
                "error": f"Location '{location}' not found",
                "suggestions": "Try using a more specific address or well-known landmark name"
            }
        
        # Process results
        if exactly_one:
            processed_result = {
                "location": location,
                "coordinates": {
                    "latitude": float(result.latitude),
                    "longitude": float(result.longitude)
                },
                "address": result.address,
                "raw_data": result.raw,
                "search_timestamp": datetime.now().isoformat()
            }
        else:
            processed_result = {
                "location": location,
                "multiple_results": [
                    {
                        "coordinates": {
                            "latitude": float(r.latitude),
                            "longitude": float(r.longitude)
                        },
                        "address": r.address,
                        "raw_data": r.raw
                    } for r in result
                ],
                "search_timestamp": datetime.now().isoformat()
            }
        
        return processed_result
        
    except (GeocoderTimedOut, GeocoderUnavailable) as e:
        return {"error": f"Geocoding service error: {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}

@mcp.tool()
def calculate_distance(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
    unit: str = "km"
) -> Dict[str, Any]:
    """Calculates geodetic distance between two geographic coordinates. Takes latitude/longitude pairs for two locations and unit preference (km, miles, nm). Returns distance in requested unit plus all formats. Use for route optimization, travel time estimation, and itinerary planning."""
    
    try:
        from geopy.distance import geodesic
        
        point1 = (lat1, lon1)
        point2 = (lat2, lon2)
        
        # Calculate distance
        distance = geodesic(point1, point2)
        
        # Convert to requested unit
        if unit.lower() == "miles":
            distance_value = distance.miles
        elif unit.lower() == "nm":
            distance_value = distance.nautical
        else:  # default to kilometers
            distance_value = distance.kilometers
        
        result = {
            "point1": {"latitude": lat1, "longitude": lon1},
            "point2": {"latitude": lat2, "longitude": lon2},
            "distance": {
                "value": round(distance_value, 2),
                "unit": unit.lower()
            },
            "all_units": {
                "kilometers": round(distance.kilometers, 2),
                "miles": round(distance.miles, 2),
                "nautical_miles": round(distance.nautical, 2)
            },
            "calculation_timestamp": datetime.now().isoformat()
        }
        
        return result
        
    except Exception as e:
        return {"error": f"Distance calculation error: {str(e)}"}


# =====================================================================
# FINANCIAL TOOLS
# =====================================================================

@mcp.tool()
def convert_currency(
    from_currency: str,
    to_currency: str,
    amount: float = 1.0,
    language: str = "en"
) -> Dict[str, Any]:
    """Converts amounts between currencies using real-time exchange rates via ExchangeRate-API. Takes source and target currency codes (USD, EUR, GBP, etc.), optional amount (default 1.0), returns converted amount and current exchange rate. Essential for international travel budgeting, expense tracking, and price comparisons across currencies."""
    try:
        api_key = get_exchange_rate_api_key()
        base_url = f"https://v6.exchangerate-api.com/v6/{api_key}/pair/{from_currency.upper()}/{to_currency.upper()}"
        response = requests.get(base_url, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get("result") != "success":
            return {"error": data.get("error-type") or "ExchangeRate-API error"}

        rate = data.get("conversion_rate")
        if rate is None:
            return {"error": "Conversion rate not available"}

        converted_amount = round(amount * float(rate), 2)

        processed_results = {
            "search_metadata": {
                "from_currency": from_currency.upper(),
                "to_currency": to_currency.upper(),
                "amount": amount,
                "search_timestamp": datetime.now().isoformat(),
                "provider": "exchangerate-api",
            },
            "exchange_rate": rate,
            "conversion": {
                "original_amount": amount,
                "converted_amount": converted_amount,
                "rate": rate,
            },
        }
        return processed_results
    except requests.exceptions.RequestException as e:
        return {"error": f"Currency API request failed: {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}


# =====================================================================
# UNIFIED PROMPTS
# =====================================================================

@mcp.prompt()
def travel_planning_prompt(
    destination: str,
    departure_location: str = "",
    travel_dates: str = "",
    travelers: int = 1,
    budget: str = "",
    interests: str = "",
    travel_style: str = ""
) -> str:
    """Generates comprehensive AI travel planning guidance combining flight booking, hotel searches, activities, and itinerary optimization. Provides personalized recommendations based on budget, duration, interests, and travel constraints."""
    
    prompt = f"""🌟 **WELCOME TO YOUR COMBINED TRAVEL CONCIERGE SERVICE** 🌟

I'm your comprehensive AI travel specialist with access to BOTH Google Travel Services AND Amadeus Professional Systems! Let me plan your perfect journey to {destination}"""
    
    if departure_location:
        prompt += f" from {departure_location}"
    
    if travel_dates:
        prompt += f" for {travel_dates}"
    
    prompt += f" for {travelers} traveler{'s' if travelers != 1 else ''}."
    
    if budget:
        prompt += f"\n💰 **Budget**: {budget}"
    
    if interests:
        prompt += f"\n🎯 **Your Interests**: {interests}"
    
    if travel_style:
        prompt += f"\n✈️ **Travel Style**: {travel_style}"
    
    prompt += """
# YOUR COMPLETE DUAL-POWERED TRAVEL EXPERIENCE

## Phase 0 — Swiss Rail & Ground Transport Planning
**For Switzerland destinations, leverage the specialized Swiss MCP ecosystem:**

- **Journey Planning** — `journey-service-mcp` provides 8 SBB rail planning tools:
  - `journey__find_trips` — Real-time train connections with live delays/platforms
  - `findStopPlacesByName` — Station search across Switzerland
  - `getPlaceEvents` — Live departure boards
  - `compareRoutes` — Multi-criteria journey comparison
  - `getEcoComparison` — CO2 emissions analysis

- **Rail Ticketing** — `swiss-mobility-mcp` provides 8 booking tools:
  - `mobility__get_trip_pricing` — Calculate SBB ticket prices
  - `createBooking` — Book and confirm reservations
  - `getTicketPdf` — Download PDF tickets

- **Swiss Tourism** — `swiss-tourism-mcp` provides 21 tools for attractions:
  - `tourism__search_sights` — 283 curated Swiss attractions
  - `tourism__search_railaway_products` — 133 rail+attraction combos
  - `tourism__plan_multi_day_trip` — Multi-day Swiss itineraries

- **Swiss Weather** — `open-meteo-mcp` provides 11 weather tools:
  - `meteo__get_weather` — Detailed forecasts for Swiss locations
  - `meteo__get_snow_conditions` — Mountain snow reports
  - `meteo__get_comfort_index` — Activity comfort scoring

**Orchestration Pattern:** Use these MCPs for Switzerland trips, then fall back to global tools for international segments.

## Phase 1 — Flight Discovery & Comparison (with Accessibility)
- **Google Flights Search** — use `search_flights_serpapi()` for consumer flight options.
  - *Accessibility note:* Results include guidance on IATA Special Service Request (SSR) codes: WCHR (wheelchair), WCHS (wheelchair with stowage), STCR (stretcher), DEAF, BLND, PRMK (mobility disability).
- **Amadeus Professional Search** — use `search_flights_amadeus()` for professional airline inventory.
  - *Accessibility note:* Results include accessibility information and SSR code recommendations.
- Compare results from both systems to find the best deals, access consumer and agent data, and get price insights and schedule optimization.
- **For accessibility requirements:** Contact airline directly with appropriate SSR codes, note special meal requests, and request accessible seating.

## Phase 2 — Hotel & Accommodation Discovery (with Accessibility)
- **Google Hotels** — `search_hotels_serpapi()` for consumer options (vacation rentals, reviews, special offers).
  - *Accessibility note:* Amenity ID 53 indicates wheelchair accessible rooms. Results include accessibility indicators.
- **Amadeus Hotel Search** — `search_hotels_amadeus_by_city()` or `search_hotels_amadeus_by_geocode()` for professional inventory.
  - *Accessibility note:* Results include facility lists with accessibility information (elevators, accessible bathrooms, parking, etc.).
- **Professional Hotel Offers** — `search_hotel_offers_amadeus()` for real-time availability and pricing.
  - *Accessibility note:* Availability includes accessible room inventory and facility details.
- Compare pricing and availability across both platforms.
- **For accessibility requirements:** Filter by wheelchair accessibility, accessible bathroom types (roll-in shower, grab bars), accessible parking, accessible entrance, and service animal policies.

## Phase 3 — Events & Activities Discovery
- **Google Events** — `search_events_serpapi()` for local events, concerts, and festivals.
- **Amadeus Activities** — `search_tours_activities_amadeus()` for professional tours and curated experiences.
- Use both to combine consumer events and professional offerings.

## Phase 4 — Location Intelligence & Navigation
- Use `geocode_location()` to get precise coordinates for destinations.
- Use `calculate_distance()` to optimize routes and daily itineraries.
- Map efficient daily routes between attractions, hotels, and activities.

## Phase 5 — Weather Intelligence & Activity Planning
- Use `get_weather_forecast()` to understand conditions during the visit.
- Use `get_current_conditions()` for real-time weather updates.
- Plan activities around optimal weather windows.

## Phase 6 — Financial Planning & Currency Strategy
- Use `convert_currency()` for accurate budget planning and expense tracking.
- Track exchange rates and optimize currency conversion timing.

## Presentation Style
Present everything as an expert travel friend with access to BOTH consumer and professional travel platforms: provide detailed comparisons, insider tips, and comprehensive travel plans.

## Available Dual-Platform Tools

**Flight search**
- `search_flights_serpapi()` — Google Flights (consumer)
- `search_flights_amadeus()` — Amadeus GDS (professional)

**Hotel search**
- `search_hotels_serpapi()` — Google Hotels (consumer)
- `search_hotels_amadeus_by_city()` — Amadeus professional city search
- `search_hotels_amadeus_by_geocode()` — Amadeus professional coordinate search
- `search_hotel_offers_amadeus()` — Amadeus real-time offers and availability

**Events & activities**
- `search_events_serpapi()` — Google Events (consumer)
- `search_tours_activities_amadeus()` — Amadeus professional activities
- `get_activity_details_amadeus()` — Detailed activity information

**Location & utilities**
- `geocode_location()` — Precise location finding
- `calculate_distance()` — Route optimization
- `get_weather_forecast()` — Weather planning
- `get_current_conditions()` — Real-time weather
- `convert_currency()` — Financial planning

**Swiss Rail & Tourism Ecosystem** (External MCPs - configure separately)
- `journey__find_trips()` — SBB rail journey planning
- `mobility__get_trip_pricing()` — Swiss rail ticket pricing
- `tourism__search_sights()` — Swiss attractions search
- `tourism__search_railaway_products()` — Rail+attraction combos
- `meteo__get_weather()` — Swiss weather forecasts
- `meteo__get_snow_conditions()` — Mountain conditions

Let's create your perfect travel experience using BOTH consumer and professional travel platforms, enhanced with Swiss-specific services!
"""

    return prompt

@mcp.resource("travel://combined/capabilities")
def combined_travel_server_capabilities() -> str:
    """Provides comprehensive reference documentation for all travel server capabilities. Returns detailed guide covering dual-platform tools (Google/SerpAPI and Amadeus), features, API requirements, best practices, and integration strategies for flight, hotel, activity, weather, location, and financial planning."""
    
    return """# Combined Travel Concierge Server - Complete Capabilities Guide

## Overview
This combined server integrates the best of both consumer travel platforms (Google via SerpAPI) AND professional travel industry systems (Amadeus GDS) into one powerful platform, providing unparalleled travel planning assistance.

## Dual Flight Search Services

### Consumer Flight Search (Google Flights via SerpAPI)
**Tool:** `search_flights_serpapi()`
- Access Google's comprehensive flight database
- Consumer-friendly pricing and schedule display
- Price insights and trend analysis
- Multi-airline comparison with popular routes
- Family-friendly search with children and infant options

### Professional Flight Search (Amadeus GDS)
**Tool:** `search_flights_amadeus()`
- Professional travel agent inventory access
- Real-time airline seat availability
- Detailed fare class information
- Professional booking codes and restrictions
- Advanced filtering by airline preferences

**Combined Benefits:**
- Compare consumer vs. professional pricing
- Access both popular routes AND hidden inventory
- Get comprehensive view of all available options
- Professional insights with consumer-friendly presentation

## Comprehensive Hotel Services

### Consumer Hotel Search (Google Hotels via SerpAPI)
**Tool:** `search_hotels_serpapi()`
- Vacation rentals, boutique hotels, major chains
- Consumer reviews and ratings
- Special offers and package deals
- Family-friendly filtering with children's ages
- Flexible cancellation and booking options

### Professional Hotel Search (Amadeus GDS)
**Tools:** 
- `search_hotels_amadeus_by_city()` - City-based professional search
- `search_hotels_amadeus_by_geocode()` - Coordinate-based search
- `search_hotel_offers_amadeus()` - Real-time availability and pricing

**Professional Features:**
- Travel industry rates and inventory
- Real-time room availability
- Professional booking codes
- Detailed property amenities and chain information
- Business travel optimized results

## 🎭 Dual Event & Activity Discovery

### Consumer Events (Google Events via SerpAPI)
**Tool:** `search_events_serpapi()`
- Local festivals, concerts, exhibitions
- Consumer-friendly event discovery
- Popular attractions and entertainment
- Virtual events and online experiences

### Professional Activities (Amadeus GDS)
**Tools:**
- `search_tours_activities_amadeus()` - Professional tour operations
- `get_activity_details_amadeus()` - Detailed activity information

**Professional Features:**
- Curated tour operators and experiences
- Professional activity bookings
- Verified experience providers
- Detailed scheduling and requirements

## Location Intelligence Services
**Tools Available:**
- `geocode_location()` - Convert addresses/places to coordinates
- `calculate_distance()` - Measure distances between locations

**Capabilities:**
- Precise location identification worldwide
- Distance calculations for route optimization
- Multi-language location details
- Address detail breakdown

## Weather Intelligence Service
**Tools Available:**
- `get_weather_forecast()` - Detailed weather forecasts
- `get_current_conditions()` - Real-time weather data

**Capabilities:**
- Daily and hourly weather forecasts using Open-Meteo
- Current temperature, humidity, wind conditions
- Activity planning based on weather conditions
- Travel safety considerations

## Financial Services
**Tools Available:**
- `convert_currency()` - Real-time currency conversion via ExchangeRate-API

**Capabilities:**
- Real-time exchange rates for international travel
- Travel industry investment tracking
- Budget planning assistance across currencies
- Financial market insights for travel investments

## Unified Planning Advantages

**Dual Platform Benefits:**
- **Best Price Discovery**: Compare consumer vs. professional rates
- **Maximum Inventory Access**: See both popular and hidden options
- **Professional + Consumer Insights**: Get industry knowledge with user-friendly presentation
- **Comprehensive Coverage**: Access the widest range of travel options available
- **Redundancy & Reliability**: If one platform has issues, the other provides backup

**Integration Benefits:**
- Single server handles all travel needs across multiple platforms
- Coordinated data sharing between consumer and professional services
- Unified error handling and comprehensive reporting
- Consistent API responses across all services

## Technical Specifications

**Required Environment Variables:**
- `SERPAPI_KEY` - Required for Google Flights, Hotels, Events, and Finance services
- `AMADEUS_API_KEY` - Required for Amadeus professional services
- `AMADEUS_API_SECRET` - Required for Amadeus professional services
- `EXCHANGE_RATE_API_KEY` - Required for currency conversion services

**Dependencies:**
- requests (API calls)
- geopy (geocoding services)
- amadeus (Amadeus GDS access)
- mcp.server.fastmcp (MCP server framework)

**Error Handling:**
- Graceful API failure handling across all platforms
- Fallback mechanisms between consumer and professional services
- Comprehensive error reporting with platform identification
- Timeout management and rate limiting compliance

## 🇨🇭 Swiss Travel Ecosystem Integration

This server is part of a **federated MCP ecosystem** for comprehensive Swiss travel planning. When planning Switzerland trips, leverage these specialized companion servers:

### Journey Service MCP (Rail Planning)
**Server:** `journey-service-mcp`
**Capabilities:**
- Real-time SBB train connections with live delays and platform information
- 126+ stations across Switzerland and neighboring countries

**♿ Accessibility Features:**
- Wheelchair-accessible route planning with 4 accessibility levels (self-boarding, crew assistance, notification-required, shuttle-transport)
- Train accessibility data: wheelchair spaces, accessible toilets, visual impairment aids
- Optimized transfer times for mobility-restricted travelers (10+ minute minimum)
- Real-time platform accessibility information

**🌍 Ecology Features:**
- CO2 emissions analysis comparing train vs car vs plane
- Eco-friendly route recommendations with tree offset calculations
- Train-based travel routing (lowest carbon footprint for ground transport)

**Additional Features:**
- Train formation data (car layout, amenities, WiFi zones)

**Key Tools:**
- `journey__find_trips` — Search train journeys with real-time data
- `findStopPlacesByName` — Find stations by name
- `getPlaceEvents` — Live departure boards
- `compareRoutes` — Compare journey options by multiple criteria
- `getEcoComparison` — CO2 emissions analysis

### Swiss Mobility MCP (Rail Ticketing)
**Server:** `swiss-mobility-mcp`
**Capabilities:**
- SBB ticket pricing with Half-Fare and GA pass support
- Booking and reservation management
- PDF ticket generation
- Refund processing

**Key Tools:**
- `mobility__get_trip_pricing` — Calculate SBB fares
- `createBooking` — Create reservations
- `getTicketPdf` — Download PDF tickets
- `cancelBooking` — Cancel reservations

### Swiss Tourism MCP (Attractions & Packages)
**Server:** `swiss-tourism-mcp`
**Capabilities:**
- 283 curated Swiss attractions with detailed information
- 133 RailAway combo offers (rail + attraction bundles)
- 19 Swiss Travel System products (passes, discount cards)
- 12 holiday packages from Switzerland Travel Centre
- 10 Alpine resorts with seasonal information
- Multi-day trip planning

**♿ Accessibility Features:**
- Barrier-free attraction filtering: wheelchair, mobility, pet-friendly, stroller-compatible
- Comprehensive accessible tourism planning with dedicated prompt covering:
  - Wheelchair-accessible attractions and accommodations
  - Level boarding and accessible transport connections
  - Hotels with roll-in showers and accessible bathrooms
  - Sensory, cognitive, dietary, and medical needs assessment
  - Accessible parking and resting areas

**🌍 Ecology Features:**
- RailAway combo packages promote train+attraction efficiency (lowest carbon option)
- Multi-day trip planning encourages longer stays (reduced travel frequency)

**Key Tools:**
- `tourism__search_sights` — Search attractions by category/vibe tags
- `tourism__search_railaway_products` — Rail+attraction combos
- `tourism__plan_multi_day_trip` — Generate Swiss itineraries
- `tourism__search_resorts` — Alpine resort search

### Open-Meteo MCP (Weather Intelligence)
**Server:** `open-meteo-mcp`
**Capabilities:**
- 16-day weather forecasts for Swiss locations
- Snow depth and mountain conditions
- Historical weather data (80+ years)
- Comfort index for outdoor activities

**♿ Accessibility Features:**
- Weather alerts for safety-critical conditions: heat, cold, storm, UV intensity
- Pollen data (Europe) for allergy-conscious travelers
- Real-time air quality index (AQI) for respiratory health planning

**🌍 Ecology Features:**
- Air quality monitoring: CO, NO₂, SO₂, O₃ levels
- Environmental condition tracking for low-emission activity planning
- Weather-based activity optimization (reducing unnecessary travel)

**Key Tools:**
- `meteo__get_weather` — Detailed forecasts
- `meteo__get_snow_conditions` — Mountain snow reports
- `meteo__get_air_quality` — AQI and pollen levels
- `meteo__get_comfort_index` — Activity comfort score

### Cross-Server Orchestration Examples

**Complete Switzerland Trip Planning:**
1. Use `meteo__get_weather()` to check conditions
2. Use `tourism__search_sights()` to find attractions
3. Use `journey__find_trips()` to plan rail connections
4. Use `mobility__get_trip_pricing()` to get ticket costs
5. Use `tourism__search_railaway_products()` for combo deals
6. Use `search_hotels_serpapi()` (this server) for accommodation
7. Use `meteo__get_comfort_index()` to optimize activities

**♿ Accessible Trip Planning:**
1. Use `journey__find_trips()` with wheelchair accessibility filters
2. Use `tourism__search_sights()` with barrier-free attraction filters
3. Use `meteo__get_weather_alerts()` for health/safety conditions
4. Identify wheelchair spaces on trains via `getTrainFormation()`
5. Use `tourism__plan_multi_day_trip()` with accessible accommodation
6. Use `mobility__get_trip_pricing()` for appropriate seating/services
7. Use `meteo__get_air_quality()` for respiratory health planning

**🌍 Eco-Conscious Trip Planning:**
1. Use `journey__find_trips()` for train-based routes (lowest CO2)
2. Use `getEcoComparison()` to compare CO2 vs car/plane
3. Use `tourism__search_railaway_products()` for efficient rail+attraction combos
4. Use `tourism__plan_multi_day_trip()` to reduce travel frequency
5. Use `meteo__get_air_quality()` to check environmental conditions
6. Optimize routes with `calculate_distance()` (this server) for minimal travel
7. Use `convert_currency()` (this server) for budget-friendly sustainable options

### Federation Setup

**Claude Desktop Configuration:**
```json
{
  "mcpServers": {
    "travel-concierge": {
      "command": "uv",
      "args": ["run", "python", "-m", "travel_assistant.server"]
    },
    "journey-service": {
      "command": "java",
      "args": ["-jar", "path/to/journey-service-mcp.jar"]
    },
    "swiss-mobility": {
      "command": "java",
      "args": ["-jar", "path/to/swiss-mobility-mcp.jar"]
    },
    "swiss-tourism": {
      "command": "uv",
      "args": ["run", "python", "-m", "swiss_tourism_mcp.server"]
    },
    "open-meteo": {
      "command": "uv",
      "args": ["run", "python", "-m", "open_meteo_mcp.server"]
    }
  }
}
```

Claude automatically orchestrates across all configured servers for Switzerland-focused trips.

## ♿ Accessibility Features

This server includes comprehensive accessibility support for travelers with mobility, sensory, or other accessibility needs:

### Flight Accessibility
- **Wheelchair & Mobility:** WCHR (wheelchair), WCHS (wheelchair with stowage), STCR (stretcher), PRMK (passenger with mobility disability)
- **Sensory Accessibility:** DEAF (deaf passenger), BLND (blind passenger)
- **Special Meals:** Diabetic, low-sodium, vegetarian, vegan options
- **Companion Support:** Option to book companion/assistant passengers
- **Accessible Lavatories:** Aircraft equipped with wheelchair-accessible restrooms
- **Extra Legroom:** Available for passengers with mobility limitations

**How to Use:**
1. Search flights with `search_flights_serpapi()` or `search_flights_amadeus()`
2. Results include accessibility guidance with IATA SSR codes
3. Contact airline directly with appropriate SSR code
4. Request accessible seat, special meals, and assistance during booking

### Hotel Accessibility
- **Wheelchair Accessible Rooms:** Detected via amenity ID 53 (Google Hotels) or facility lists (Amadeus)
- **Accessible Bathrooms:** Roll-in showers, grab bars, accessible toilets
- **Accessible Parking:** Dedicated accessible parking spaces
- **Accessible Entrance:** Level or ramped entry, automatic doors
- **Accessible Elevators:** Serving all guest floors
- **Service Animals:** Pet-friendly policies for guide dogs and service animals

**How to Use:**
1. Search hotels with `search_hotels_serpapi()` or `search_hotels_amadeus_by_city()`
2. Results include accessibility indicators:
   - Google Hotels: Amenity ID 53 = wheelchair accessible
   - Amadeus: Facility list with accessibility features
3. Check accessibility object in results for detailed information
4. Filter by specific accessibility needs (wheelchair access, bathroom type, etc.)

### Accessibility Request Model
Use `AccessibilityRequest` model to document traveler needs:
- `wheelchair_user` — Uses wheelchair (may require stowage)
- `reduced_mobility` — General reduced mobility requiring assistance
- `deaf` — Deaf traveler (needs visual alerts)
- `blind` — Blind traveler (needs audio assistance)
- `stretcher_case` — Medical condition requiring stretcher
- `companion_required` — Traveling with assistant/companion
- `special_requirements` — Additional medical or mobility needs

### Data Models
- **FlightAccessibility:** Flight-level accessibility features and SSR codes
- **HotelAccessibility:** Hotel-level accessibility features and facilities
- **AccessibilityRequest:** Traveler accessibility requirements

### Best Practices
1. **Early Communication:** Inform airlines/hotels about accessibility needs during booking
2. **SSR Codes:** Use proper IATA codes when contacting airlines
3. **Verification:** Confirm accessibility features exist before arrival
4. **Alternatives:** Have backup options in case primary choice unavailable
5. **Companion Support:** Arrange companion/assistance if needed

## 🚀 Getting Started

1. **Set Environment Variables:**
   ```bash
   export SERPAPI_KEY="your-serpapi-key"
   export AMADEUS_API_KEY="your-amadeus-client-id"
   export AMADEUS_API_SECRET="your-amadeus-client-secret"
   export EXCHANGE_RATE_API_KEY="your-exchangerate-api-key"
   ```

2. **Run the Combined Server:**
   ```bash
   python combined_travel_server.py
   ```

3. **Use the Comprehensive Planning Prompt:**
   Start with `comprehensive_travel_planning_prompt()` for full dual-platform trip planning assistance.

## 🌟 Best Practices for Dual-Platform Usage

**Flight Search Strategy:**
1. Start with Google Flights (search_flights_serpapi) for broad market overview
2. Use Amadeus (search_flights_amadeus) for professional options and detailed fare information
3. Compare results to find the absolute best deals and options

**Hotel Search Strategy:**
1. Use Google Hotels (search_hotels_serpapi) for vacation rentals and consumer-friendly options
2. Use Amadeus hotel searches for professional rates and detailed property information
3. Cross-reference availability and pricing across both platforms

**Activity Planning Strategy:**
1. Use Google Events (search_events_serpapi) for local cultural events and festivals
2. Use Amadeus Activities for professional tours and curated experiences
3. Combine both for comprehensive activity planning

**Location & Weather Integration:**
- Always start with geocoding to establish precise coordinates
- Use weather forecasts to optimize activity and travel planning
- Calculate distances to optimize daily itineraries

**Financial Planning:**
- Use currency conversion for accurate international budget planning
- Track exchange rates for optimal conversion timing

This combined server provides the most comprehensive travel planning capabilities available, leveraging both consumer platforms and professional travel industry systems! 🌎✈️🏨🎭💰"""

def main():
    """Entry point for the Travel Assistant MCP server."""
    import sys
    import argparse

    parser = argparse.ArgumentParser(description="Travel Assistant MCP Server")
    parser.add_argument("--transport", type=str, choices=["stdio", "sse", "http"], default="stdio", help="Transport type")
    parser.add_argument("--port", type=int, default=8000, help="Port for HTTP/SSE transport")

    args = parser.parse_args()

    transport_kwargs = {}
    if args.transport in ["sse", "http"]:
        transport_kwargs["port"] = args.port

    mcp.run(transport=args.transport, show_banner=True, **transport_kwargs)

if __name__ == "__main__":
    main()
