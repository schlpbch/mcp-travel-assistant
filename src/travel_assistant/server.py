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
    """Searches Google Flights for best deals and routes. Takes departure location, arrival destination, outbound date, optional return date, passenger counts by type (adults, children, infants), seat class, currency, language, and max results. Returns curated flight options with prices, schedules, and airline booking links ranked by value."""
    
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
        }

        if return_date and trip_type == 1:  # Round trip
            params["return_date"] = return_date

        # Make API request (client handles engine, api_key, timeout)
        flight_data = serpapi_client.search_flights(**params)
        
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
                "search_timestamp": datetime.now().isoformat()
            },
            "best_flights": flight_data.get("best_flights", [])[:max_results],
            "other_flights": flight_data.get("other_flights", [])[:max_results],
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
    """Searches Amadeus Global Distribution System for professional flight offers. Takes departure/arrival airport codes (IATA), travel dates, passenger counts, seat classes, airline filters, and optional preferences. Returns curated flight options with pricing, schedules, seat availability, and booking confirmation numbers."""
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
        
        # Process hotel results
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
            "properties": hotel_data.get("properties", [])[:max_results],
            "filters": hotel_data.get("filters", {}),
            "search_parameters": hotel_data.get("search_parameters", {}),
            "location_info": hotel_data.get("place_results", {})
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

## Phase 0 — Rail & Ground Transport Planning

## Phase 1 — Flight Discovery & Comparison
- **Google Flights Search** — use `search_flights_serpapi()` for consumer flight options.
- **Amadeus Professional Search** — use `search_flights_amadeus()` for professional airline inventory.
- Compare results from both systems to find the best deals, access consumer and agent data, and get price insights and schedule optimization.

## Phase 2 — Hotel & Accommodation Discovery
- **Google Hotels** — `search_hotels_serpapi()` for consumer options (vacation rentals, reviews, special offers).
- **Amadeus Hotel Search** — `search_hotels_amadeus_by_city()` or `search_hotels_amadeus_by_geocode()` for professional inventory.
- **Professional Hotel Offers** — `search_hotel_offers_amadeus()` for real-time availability and pricing.
- Compare pricing and availability across both platforms.

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

Let's create your perfect travel experience using BOTH consumer and professional travel platforms!
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
