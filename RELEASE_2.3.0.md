# Release v2.3.0 - Accessibility Features

**Date:** January 20, 2026
**Version:** 2.3.0 (from 2.2.0)
**Status:** ✅ Released and tested (182/182 tests passing)

## Overview

Release 2.3.0 adds **comprehensive accessibility support** to the travel concierge MCP server, enabling personalized trip planning for travelers with mobility impairments and sensory disabilities. This release includes 3 new Pydantic models, 3 helper functions, 3 new MCP prompts, and 26 new tests covering all accessibility scenarios.

## Major Features

### 1. Accessibility Data Models (3 Pydantic Models, 26 Fields)

#### FlightAccessibility
- `wheelchair_available`: Wheelchair seating/accommodation
- `wheelchair_stowage`: Wheelchair can be stowed in cargo
- `accessible_lavatory`: Aircraft has accessible restroom
- `extra_legroom_available`: Extra legroom for mobility impaired
- `special_service_codes`: IATA SSR codes (WCHR, WCHS, STCR, DEAF, BLND, PRMK)
- `companion_required`: Companion/escort passenger needed
- `special_meals_available`: Special dietary options
- `notes`: Airline accessibility information

#### HotelAccessibility
- `wheelchair_accessible`: Wheelchair accessible rooms available
- `accessible_room_available`: Accessible rooms in stock
- `wheelchair_amenity_id`: SerpAPI amenity ID reference (53)
- `accessible_bathroom_types`: Roll-in shower, grab bars, etc.
- `accessible_parking`: Handicap parking spaces
- `accessible_entrance`: Level or ramped entrance
- `accessible_elevator`: Accessible elevator access
- `service_animals_allowed`: Guide dogs/service animals policy
- `lowest_accessible_price`: Price of least expensive accessible room
- `facility_list`: Complete list of accessibility features

#### AccessibilityRequest
- `wheelchair_user`: Traveler uses wheelchair
- `reduced_mobility`: General reduced mobility
- `deaf`: Deaf traveler (needs visual alerts)
- `blind`: Blind traveler (needs audio assistance)
- `stretcher_case`: Medical requirement for stretcher
- `companion_required`: Companion/escort traveling
- `special_requirements`: Additional mobility/medical needs

### 2. Automatic Accessibility Extraction

**SerpAPI Hotels:**
- Detects wheelchair accessibility from amenity ID 53
- Returns structured accessibility data per hotel

**SerpAPI Flights:**
- Provides IATA SSR code guidance
- References airline contact for special requests

**Amadeus Hotels:**
- Extracts facilities with accessibility keywords
- Case-insensitive matching for: wheelchair, accessible, mobility, elevator, ramp, parking, bathroom

**Amadeus Flights:**
- Extracts special service request codes
- Returns FlightAccessibility object with all details

### 3. Enhanced Search Functions

**search_flights_amadeus():**
```python
# Now returns accessibility object
{
  "id": "1",
  ...flight_data...,
  "accessibility": {
    "wheelchair_available": false,
    "special_service_codes": null,
    "notes": "Check with airline..."
  },
  "accessibility_included": true
}
```

**search_flights_serpapi():**
```python
# Now includes accessibility note
"accessibility_note": "For accessibility requirements (wheelchair, deaf, blind, stretcher),
contact airlines directly with IATA Special Service Request (SSR) codes:
WCHR (wheelchair), WCHS (wheelchair with stowage), STCR (stretcher), DEAF, BLND, PRMK"
```

**search_hotels_serpapi():**
```python
# Each hotel now includes accessibility data
{
  "name": "Hotel Name",
  ...hotel_data...,
  "accessibility": {
    "wheelchair_accessible": true,
    "accessible_room_available": true,
    "wheelchair_amenity_id": 53
  }
}
```

### 4. Three New MCP Prompts

#### accessible_trip_planner
**Purpose:** Comprehensive personalized accessible trip planning
**Lines:** 1,500+
**Features:**
- Collects accessibility needs (mobility types, sensory requirements, companion needs)
- Analyzes global flight accessibility with SSR codes
- Filters hotels for accessibility features
- Plans accessible activities and attractions
- Builds contingency plans for accessibility barriers
- Provides step-by-step recommendations

#### wheelchair_accessible_itinerary
**Purpose:** Day-by-day barrier-free wheelchair itineraries
**Lines:** 1,100+
**Features:**
- Collects wheelchair specifications (manual/electric, dimensions, assistance)
- Analyzes accessibility at each location
- Builds step-by-step daily plans with elevation maps
- Provides contingency strategies
- Includes detailed accessibility checklists

#### sensory_accessible_travel
**Purpose:** Travel planning for deaf/blind/deaf-blind travelers
**Lines:** 1,200+
**Features:**
- Deaf traveler guidance (visual alerts, captioning, sign language)
- Blind traveler guidance (tactile info, audio assistance, guide dogs)
- Deaf-blind guidance (tactile signing, specialized assistance)
- Flight accommodation strategies
- Hotel features for sensory accessibility
- Activity recommendations with adaptations

### 5. Enhanced Documentation

**travel_planning_prompt:**
- Phase 1: Flight search accessibility guidance
- Phase 2: Hotel search accessibility guidance
- IATA SSR codes explanation
- Accessibility filtering recommendations

**combined_travel_server_capabilities:**
- New "♿ Accessibility Features" section (1,200+ lines)
- 3 new Pydantic models documented
- Extraction methods explained
- IATA SSR code reference
- Best practices for accessible planning
- 3 new MCP prompts with use cases

## IATA Special Service Request Codes

Airlines coordinate accessibility accommodations using these codes:

| Code | Meaning |
|------|---------|
| WCHR | Wheelchair assistance (passenger provides own wheelchair) |
| WCHS | Wheelchair with stowage (wheelchair stowed in cargo) |
| STCR | Stretcher case (medical requirement) |
| DEAF | Deaf passenger (visual alerts, no audio announcements) |
| BLND | Blind passenger (audio assistance, guide dog accommodation) |
| PRMK | Passenger with mobility disability (priority seating, assistance) |

## Testing

**26 new accessibility tests:**
- Hotel accessibility extraction (5 tests)
- Amadeus hotel accessibility (5 tests)
- Flight accessibility extraction (3 tests)
- Accessibility request creation (5 tests)
- Accessibility scenarios (3 tests)
- Data validation (5 tests)

**Test results:**
- ✅ 182/182 tests passing
- ✅ 0 regressions
- ✅ 100% backward compatible

## Documentation

### New Files
- `docs/ACCESSIBILITY_IMPLEMENTATION.md` (637 lines)

### Modified Files
- `src/travel_assistant/models.py` - Added 3 Pydantic models
- `src/travel_assistant/helpers.py` - Added 3 extraction helpers
- `src/travel_assistant/server.py` - Enhanced search functions, added 3 prompts
- `pyproject.toml` - Version bumped to 2.3.0

## Git Commits in This Release

```
8eb425e chore(release): bump version to 2.3.0 - Accessibility Features
93845dc feat: add comprehensive accessibility data implementation guide
4d20a3a feat: add three accessibility-focused MCP prompts
e99507a test: add comprehensive accessibility feature tests
80bbc20 feat: integrate accessibility support into flight and hotel search
a59fdaa feat: add accessibility extraction helpers
b084b5f feat: add accessibility data models
```

## Migration Notes

**Zero breaking changes:**
- All existing functionality unchanged
- New accessibility fields are optional
- All new fields don't affect existing workflows
- All 182 tests passing with zero regressions

**Integration for users:**
- Accessibility data automatically extracted from APIs
- No configuration changes required
- Optional - use accessibility features when planning for travelers with needs
- Backward compatible with existing workflows

## API Response Examples

### Search Flights (Amadeus)
```json
{
  "id": "1",
  "type": "flight-offer",
  "source": "GDS",
  "instantTicketingRequired": false,
  "nonHomogeneous": false,
  "oneWay": false,
  "lastTicketingDate": "2025-02-20",
  "numberOfBookableSeats": 4,
  "itineraries": [...],
  "accessibility": {
    "wheelchair_available": false,
    "wheelchair_stowage": false,
    "accessible_lavatory": false,
    "extra_legroom_available": false,
    "special_service_codes": null,
    "companion_required": null,
    "special_meals_available": false,
    "notes": "Check with airline for specific accessibility accommodations"
  },
  "accessibility_included": true
}
```

### Search Hotels (SerpAPI)
```json
{
  "name": "Accessible Hotel",
  "rating": 4.5,
  "type": "hotel",
  "amenities": [
    {"id": 1, "name": "WiFi"},
    {"id": 53, "name": "Wheelchair accessible"},
    {"id": 5, "name": "Parking"}
  ],
  "accessibility": {
    "wheelchair_accessible": true,
    "accessible_room_available": true,
    "wheelchair_amenity_id": 53,
    "amenities": [...]
  }
}
```

## Known Limitations

1. **Amadeus Flight API** doesn't expose accessibility details in standard response
   - Returns conservative defaults
   - Recommends direct airline contact for detailed info

2. **SerpAPI Hotels** limited to what partner APIs expose
   - Wheelchair detection limited to amenity ID 53
   - Partner data accuracy depends on hotel data entry

3. **Real-time seat availability** not available from APIs
   - Recommend airline contact for specific seat assignments
   - SSR codes submitted during booking process

## Accessibility Best Practices

1. **Always verify accessibility details directly with providers** - API data is reference only
2. **Contact airlines 48-72 hours before travel** for special requests
3. **Request specific accommodations** - wheelchair type, service animal, dietary needs
4. **Confirm hotel accessibility features match requirements** - visit hotel site/call
5. **Plan buffer time** for accessibility-related boarding/disembarking
6. **Have contingency plans** for accessibility barriers

## Future Enhancements

- Real-time seat map availability from airlines
- Additional accommodation APIs with accessibility filtering
- Integration with wheelchair taxi services
- Accessibility ratings from travelers with disabilities
- Predictive accessibility scoring for recommendations
- Multi-language accessibility guidance

## Testing Command

```bash
# Run all tests
uv run pytest tests/ -v

# Run accessibility tests only
uv run pytest tests/test_accessibility.py -v

# Run with coverage
uv run pytest tests/ --cov=src --cov-report=html
```

## Deployment

```bash
# Run the server
uv run python -m travel_assistant.server

# Or with FastMCP CLI
uv run fastmcp run src/travel_assistant/server.py
```

## Release Notes Summary

This release makes travel planning accessible to everyone. We're committed to inclusivity and ensuring travelers with disabilities have the same access to travel information and planning tools as anyone else.

**7 commits** focusing on accessibility features and testing.
**26 new tests** with comprehensive coverage of all accessibility scenarios.
**3 new MCP prompts** providing guided, step-by-step accessible trip planning.
**Zero breaking changes** - fully backward compatible.

---

**Enjoy accessible travel planning! 🌍♿**

For questions or issues, please refer to the [Accessibility Implementation Guide](docs/ACCESSIBILITY_IMPLEMENTATION.md).
