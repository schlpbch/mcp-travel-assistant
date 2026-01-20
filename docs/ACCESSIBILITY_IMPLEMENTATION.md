# Accessibility Data Implementation Guide

## Executive Summary

This document outlines the accessibility features available in SerpAPI (Google Flights/Hotels) and Amadeus GDS APIs, along with a detailed implementation plan to integrate persons with reduced mobility (PRM) support into the Travel Assistant MCP.

**Status:** ✅ APIs support accessibility features | 🚧 Implementation ready to begin

---

## Table of Contents

1. [API Capabilities Analysis](#api-capabilities-analysis)
2. [Accessible Data Available](#accessible-data-available)
3. [Implementation Plan](#implementation-plan)
4. [Data Models](#data-models)
5. [Integration Steps](#integration-steps)
6. [Testing Strategy](#testing-strategy)

---

## API Capabilities Analysis

### SerpAPI (Google Flights & Hotels)

#### Google Flights
- **Accessibility Support:** Limited
- **Available Parameters:** Standard passenger configuration only
  - `adults`, `children`, `infants_in_seat`, `infants_on_lap`
  - `travel_class` (Economy, Premium Economy, Business, First)
  - No specific wheelchair seating or mobility aid parameters in request
- **Response Data:** Flights returned from Google Flights may include accessibility information in airline data
- **Limitation:** No specialized accessibility request parameters documented

#### Google Hotels
- **Accessibility Support:** YES ✅
- **Available Amenities:** Amenity ID **53** = "Wheelchair accessible"
- **Filtering:** Through existing `amenities` parameter
- **Response Data:** Hotel amenity lists include wheelchair accessibility status
- **Limitation:** Only wheelchair access; no other mobility accommodation types

### Amadeus GDS

#### Flight Offers Search API
- **Accessibility Support:** YES ✅ (via Special Service Requests)
- **SSR Codes for Accessibility:**
  - **WCHR** - Wheelchair passenger
  - **WCHS** - Wheelchair storage only
  - **STCR** - Stretcher case requiring crew assistance
  - **DEAF** - Deaf passenger
  - **BLND** - Blind passenger
  - **PRMK** - Mobility impaired (general)
- **Implementation:** Added via PNR (Passenger Name Record) after search
- **Escort Support:** Separate OSI (Other Service Information) for accompanying personnel
- **Wheelchair Policy:** Free checked baggage for dependent wheelchairs
- **Limitation:** SSR codes added post-search, not in initial search parameters

#### Hotel Search API
- **Accessibility Support:** YES ✅
- **Available Data:** Hotel room accessibility information included in responses
- **Features:**
  - Wheelchair accessibility room availability
  - Least expensive accessible room pricing highlighted
  - Facility accessibility details in hotel data
- **Filtering:** Accessibility data in hotel facility descriptions
- **Limitation:** Limited advanced filtering; data returned in response

---

## Accessible Data Available

### From SerpAPI

#### Hotels
| Feature | Status | Data Location |
|---------|--------|----------------|
| Wheelchair accessible indicator | ✅ | Amenity ID 53 in amenities array |
| Accessible room availability | ✅ | Property details |
| Accessible facilities count | ✅ | Amenities list |
| Room type specifications | ⚠️ | Limited in consumer API |

#### Flights
| Feature | Status | Notes |
|---------|--------|-------|
| Wheelchair seating requests | ❌ | Not in Google Flights consumer API |
| Mobility aid accommodation | ❌ | Not available |
| Accessible lavatories | ❌ | Not available |
| Extra legroom options | ⚠️ | May be in seat type data |

### From Amadeus

#### Flights
| Feature | Status | Implementation |
|---------|--------|-----------------|
| SSR wheelchair codes | ✅ | WCHR, WCHS, STCR, DEAF, BLND, PRMK |
| Escort information | ✅ | Via OSI fields |
| Wheelchair baggage policy | ✅ | Standard Amadeus policy |
| Extra legroom/seat selection | ⚠️ | Via seat availability |
| Special meal requests | ✅ | Via SSR codes (VGML, LFML, etc.) |

#### Hotels
| Feature | Status | Data Location |
|---------|--------|----------------|
| Wheelchair accessible rooms | ✅ | Facility details |
| Accessible bathroom types | ✅ | Facility descriptions |
| Accessible parking | ⚠️ | In facility data |
| Pet-friendly accessible | ⚠️ | Combined amenities |
| Roll-in shower availability | ✅ | Room facility details |
| Grab bars/safety features | ✅ | Accessibility info |

---

## Implementation Plan

### Phase 1: Data Models

Create Pydantic models to standardize accessibility data across both platforms:

#### Flight Accessibility Model

```python
class FlightAccessibility(BaseModel):
    """Accessibility features for flights."""
    wheelchair_available: bool = Field(
        False,
        description="Wheelchair seating/accommodation available"
    )
    wheelchair_stowage: bool = Field(
        False,
        description="Wheelchair stowage in cargo hold"
    )
    accessible_lavatory: bool = Field(
        False,
        description="Accessible lavatory on aircraft"
    )
    extra_legroom_available: bool = Field(
        False,
        description="Extra legroom seating available"
    )
    special_service_codes: Optional[List[str]] = Field(
        None,
        description="Amadeus SSR codes (WCHR, STCR, DEAF, BLND, PRMK, etc.)"
    )
    companion_required: Optional[bool] = Field(
        None,
        description="Companion/escort passenger required"
    )
    notes: Optional[str] = Field(
        None,
        description="Additional accessibility information"
    )
```

#### Hotel Accessibility Model

```python
class HotelAccessibility(BaseModel):
    """Accessibility features for hotels."""
    wheelchair_accessible: bool = Field(
        False,
        description="Hotel has wheelchair accessible rooms"
    )
    accessible_room_available: bool = Field(
        False,
        description="Accessible rooms currently available"
    )
    accessible_bathroom_type: Optional[str] = Field(
        None,
        description="Type of accessible bathroom (roll-in shower, grab bars, accessible toilet, etc.)"
    )
    accessible_parking: bool = Field(
        False,
        description="Accessible parking spaces available"
    )
    accessible_entrance: bool = Field(
        False,
        description="Level or ramped entrance for wheelchair access"
    )
    accessible_elevator: bool = Field(
        False,
        description="Accessible elevator to floors"
    )
    pet_friendly_accessible: bool = Field(
        False,
        description="Service animals/pets allowed in accessible rooms"
    )
    lowest_accessible_price: Optional[float] = Field(
        None,
        description="Price of least expensive accessible room"
    )
    facility_details: Optional[List[str]] = Field(
        None,
        description="List of accessibility features/facilities"
    )
```

#### Accessibility Request Model

```python
class AccessibilityRequest(BaseModel):
    """Accessibility requirements for trip planning."""
    wheelchair_user: bool = Field(
        False,
        description="Traveler uses wheelchair"
    )
    reduced_mobility: bool = Field(
        False,
        description="General reduced mobility assistance needed"
    )
    deaf: bool = Field(
        False,
        description="Deaf traveler requires visual alerts"
    )
    blind: bool = Field(
        False,
        description="Blind traveler requires audio assistance"
    )
    stretcher_case: bool = Field(
        False,
        description="Stretcher case requiring medical equipment"
    )
    companion_required: bool = Field(
        False,
        description="Companion/escort passenger traveling with accessible passenger"
    )
    special_requirements: Optional[str] = Field(
        None,
        description="Additional accessibility requirements or medical needs"
    )
```

---

## Accessible Data Available

### 1. SerpAPI Hotel Wheelchair Filtering

**Location:** Hotel amenities array
**Amenity ID:** 53 = "Wheelchair accessible"
**Current Implementation:** Not extracted
**Required Change:** Parse amenities array for ID 53

```python
# Current: amenities is generic filter parameter
# Expected response structure:
{
    "hotels": [
        {
            "name": "Accessible Hotel",
            "amenities": [
                {"id": 53, "name": "Wheelchair accessible"},
                {"id": 14, "name": "WiFi"},
                ...
            ]
        }
    ]
}
```

**Implementation:** Extract amenity 53 and set `wheelchair_accessible: true`

### 2. Amadeus Flight Special Service Requests

**Available SSR Codes:**

| Code | Meaning | Use Case |
|------|---------|----------|
| WCHR | Wheelchair passenger | Any wheelchair user |
| WCHS | Wheelchair storage only | User has manual wheelchair for storage |
| STCR | Stretcher case | Medical emergency, requires crew assistance |
| DEAF | Deaf passenger | Hearing impairment, needs visual alerts |
| BLND | Blind passenger | Vision impairment, needs audio assistance |
| PRMK | Persons with reduced mobility | General mobility assistance |

**Implementation:**
- Add optional `accessibility_request` parameter to `search_flights_amadeus()`
- Convert accessibility request flags to SSR codes
- Pass SSR codes in PNR post-search or document in response

### 3. Amadeus Hotel Accessibility Data

**Response Includes:**
- Wheelchair accessible room flags
- Facility descriptions with accessibility features
- Pricing for accessible vs. standard rooms
- Accessibility amenities in facility list

**Implementation:**
- Parse hotel facility data
- Extract accessibility keywords (wheelchair, accessible, roll-in, grab bar, etc.)
- Create accessibility summary object

---

## Integration Steps

### Step 1: Add Accessibility Models to `models.py`

**File:** `src/travel_assistant/models.py`

**Add:**
- `FlightAccessibility` model
- `HotelAccessibility` model
- `AccessibilityRequest` model

**Status:** Ready to implement

### Step 2: Enhance Flight Search Parameters

**File:** `src/travel_assistant/server.py`

**Function:** `search_flights_serpapi()`
- **Change:** Add optional accessibility parameters
- **New Parameters:**
  - `wheelchair_user: bool = False`
  - `reduced_mobility: bool = False`
  - `special_requirements: Optional[str] = None`
- **Response Update:** Add `accessibility` field to flight results

**Function:** `search_flights_amadeus()`
- **Change:** Add SSR code generation from accessibility flags
- **New Parameters:** Same as above
- **Response Update:** Add `accessibility` field with SSR codes
- **Documentation:** Update docstring to mention accessibility support

### Step 3: Enhance Hotel Search Implementation

**File:** `src/travel_assistant/server.py`

**Function:** `search_hotels_serpapi()`
- **Change:** Extract amenity 53 from results
- **Response Update:** Add `accessibility` field to hotel results
- **Filter Update:** Document wheelchair accessibility filtering in amenities

**Function:** `search_hotels_amadeus_by_city()` & `search_hotels_amadeus_by_geocode()`
- **Change:** Parse facility data for accessibility features
- **Response Update:** Add `accessibility` field with parsed data
- **Pricing:** Extract accessible room pricing

**Function:** `search_hotel_offers_amadeus()`
- **Change:** Extract detailed accessibility from hotel offer data
- **Response Update:** Comprehensive accessibility summary

### Step 4: Update Tool Descriptions

**Flight Search Docstrings:**
- Add: "Includes accessibility features and wheelchair accommodation support"
- Document: SSR codes available for Amadeus
- Document: Wheelchair accessibility status in results

**Hotel Search Docstrings:**
- Add: "Includes wheelchair accessibility and facility information"
- Document: Accessible room availability and pricing
- Document: Accessibility feature filtering

### Step 5: Update Travel Planning Prompt

**File:** `src/travel_assistant/server.py`

**Function:** `travel_planning_prompt()`
- **Add:** Accessibility considerations to trip planning phases
- **New Section:** "Accessibility Planning Phase"
- **Guidance:** How to request accessible accommodations
- **Cross-Reference:** Swiss accessibility features in ecosystem

### Step 6: Create Comprehensive Tests

**Test Coverage:**
- ✅ Flight accessibility model validation
- ✅ Hotel accessibility model validation
- ✅ SerpAPI amenity 53 extraction
- ✅ Amadeus SSR code generation
- ✅ Accessibility filtering in responses
- ✅ Backward compatibility (no accessibility = graceful handling)

---

## Data Models

### Complete Model Definitions

```python
# =====================================================================
# ACCESSIBILITY MODELS
# =====================================================================

class FlightAccessibility(BaseModel):
    """Accessibility features and accommodations for flights."""
    wheelchair_available: bool = Field(
        False,
        description="Wheelchair seating/accommodation available"
    )
    wheelchair_stowage: bool = Field(
        False,
        description="Wheelchair can be stowed in cargo hold"
    )
    accessible_lavatory: bool = Field(
        False,
        description="Aircraft has accessible lavatory"
    )
    extra_legroom_available: bool = Field(
        False,
        description="Extra legroom seating available for mobility impaired"
    )
    special_service_codes: Optional[List[str]] = Field(
        None,
        description="Amadeus SSR codes: WCHR (wheelchair), STCR (stretcher), DEAF, BLND, PRMK"
    )
    companion_required: Optional[bool] = Field(
        None,
        description="Companion/escort passenger required for assistance"
    )
    special_meals_available: bool = Field(
        False,
        description="Special meal options (diabetic, low sodium, etc.)"
    )
    notes: Optional[str] = Field(
        None,
        description="Additional accessibility information from airline"
    )


class HotelAccessibility(BaseModel):
    """Accessibility features and accommodations for hotels."""
    wheelchair_accessible: bool = Field(
        False,
        description="Hotel has wheelchair accessible rooms available"
    )
    accessible_room_available: bool = Field(
        False,
        description="Accessible rooms currently in stock"
    )
    wheelchair_amenity_id: int = Field(
        53,
        description="SerpAPI amenity ID for wheelchair accessible (static)"
    )
    accessible_bathroom_types: Optional[List[str]] = Field(
        None,
        description="Types of accessible bathrooms (roll-in shower, grab bars, accessible toilet, etc.)"
    )
    accessible_parking: bool = Field(
        False,
        description="Accessible/handicap parking spaces available"
    )
    accessible_entrance: bool = Field(
        False,
        description="Level or ramped entrance for wheelchair access"
    )
    accessible_elevator: bool = Field(
        False,
        description="Accessible elevator serving all guest floors"
    )
    service_animals_allowed: bool = Field(
        False,
        description="Service animals/guide dogs allowed in accessible rooms"
    )
    lowest_accessible_price: Optional[float] = Field(
        None,
        description="Price of least expensive accessible room (Amadeus data)"
    )
    facility_list: Optional[List[str]] = Field(
        None,
        description="Complete list of accessibility features/facilities"
    )


class AccessibilityRequest(BaseModel):
    """Accessibility requirements for personalized trip planning."""
    wheelchair_user: bool = Field(
        False,
        description="Traveler uses wheelchair (may require stowage)"
    )
    reduced_mobility: bool = Field(
        False,
        description="General reduced mobility requiring assistance"
    )
    deaf: bool = Field(
        False,
        description="Deaf traveler (needs visual alerts on flights)"
    )
    blind: bool = Field(
        False,
        description="Blind traveler (needs audio assistance on flights)"
    )
    stretcher_case: bool = Field(
        False,
        description="Medical condition requiring stretcher/medical equipment"
    )
    companion_required: bool = Field(
        False,
        description="Companion/escort passenger traveling with accessible passenger"
    )
    special_requirements: Optional[str] = Field(
        None,
        description="Additional mobility or medical needs (allergies, equipment, etc.)"
    )
```

---

## Testing Strategy

### Unit Tests

**File:** `tests/test_models.py`

```python
class TestFlightAccessibility:
    """Test flight accessibility models."""

    def test_valid_flight_accessibility_all_features(self):
        """Test creating accessibility with all features enabled."""

    def test_flight_accessibility_ssr_codes(self):
        """Test SSR code assignment."""

    def test_flight_accessibility_defaults(self):
        """Test default values when not specified."""


class TestHotelAccessibility:
    """Test hotel accessibility models."""

    def test_valid_hotel_accessibility(self):
        """Test complete accessibility object."""

    def test_wheelchair_amenity_id(self):
        """Test amenity ID 53 for wheelchair."""

    def test_accessible_bathroom_types(self):
        """Test various bathroom accessibility types."""


class TestAccessibilityRequest:
    """Test accessibility request model."""

    def test_wheelchair_user_request(self):
        """Test wheelchair user accessibility request."""

    def test_companion_required_request(self):
        """Test request with companion requirement."""
```

### Integration Tests

**File:** `tests/test_clients.py`

```python
class TestAccessibilityExtraction:
    """Test accessibility data extraction from APIs."""

    def test_serpapi_amenity_53_extraction(self):
        """Test extraction of wheelchair amenity from hotel results."""

    def test_amadeus_ssr_code_generation(self):
        """Test generation of SSR codes from accessibility request."""

    def test_amadeus_hotel_accessibility_parsing(self):
        """Test parsing of facility data for accessibility."""

    def test_backward_compatibility_no_accessibility(self):
        """Test that searches work without accessibility data."""
```

---

## Implementation Priority

### Phase 1 (Immediate)
1. ✅ Create accessibility data models
2. ✅ Add Pydantic validation
3. ✅ Write unit tests for models

### Phase 2 (High Priority)
1. Extract SerpAPI amenity 53 for hotels
2. Parse Amadeus hotel accessibility facility data
3. Add accessibility parameters to hotel search functions
4. Update hotel search tool descriptions

### Phase 3 (Medium Priority)
1. Implement SSR code generation for flights
2. Add accessibility parameters to flight search functions
3. Update flight search tool descriptions
4. Add accessibility to travel planning prompt

### Phase 4 (Enhancement)
1. Add accessibility filtering to searches
2. Create accessibility-focused trip planning workflows
3. Integrate with Swiss accessibility ecosystem
4. Comprehensive documentation

---

## Success Criteria

- ✅ All accessibility models pass validation
- ✅ SerpAPI hotel wheelchair amenity (53) extracted correctly
- ✅ Amadeus SSR codes generated from accessibility request
- ✅ Amadeus hotel accessibility data parsed from facility information
- ✅ Accessibility data included in API responses
- ✅ Tool descriptions updated to mention accessibility support
- ✅ All tests passing (130+ existing + new accessibility tests)
- ✅ Backward compatibility maintained (no accessibility = graceful handling)
- ✅ Documentation updated with accessibility guidance
- ✅ Integration with Swiss ecosystem accessibility features documented

---

## References

### API Documentation
- [SerpAPI Google Hotels API](https://serpapi.com/google-hotels-api)
- [SerpAPI Supported Amenities](https://serpapi.com/google-hotels-amenities)
- [Amadeus Special Services Request Documentation](https://servicehub.amadeus.com/c/portal/view-solution/2194074/what-is-a-special-service-request-ssr-/)
- [Amadeus Flight Offers Search API](https://developers.amadeus.com/self-service/category/flights/api-doc/flight-offers-search)
- [Amadeus Hotel Search API](https://developers.amadeus.com/self-service/category/hotels/api-doc/hotel-search)

### Standards
- IATA SSR (Special Service Request) Codes
- ADA (Americans with Disabilities Act) Standards
- WCAG (Web Content Accessibility Guidelines) 2.1

---

## Next Steps

1. Review this plan with stakeholders
2. Prioritize implementation phases
3. Begin with Phase 1 (data models)
4. Coordinate with Swiss accessibility ecosystem features
5. Plan user acceptance testing with accessibility advocates

---

**Document Version:** 1.0
**Created:** January 2026
**Status:** Implementation Ready
