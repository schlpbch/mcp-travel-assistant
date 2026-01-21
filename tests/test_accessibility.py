"""Tests for accessibility features in travel assistant."""

from travel_assistant.helpers import (
    extract_amadeus_hotel_accessibility,
    extract_flight_accessibility_from_amadeus,
    extract_hotel_accessibility,
)
from travel_assistant.models import (
    AccessibilityRequest,
    FlightAccessibility,
    HotelAccessibility,
)

# =====================================================================
# HOTEL ACCESSIBILITY EXTRACTION TESTS
# =====================================================================


class TestHotelAccessibilityExtraction:
    """Test extraction of accessibility data from hotel properties."""

    def test_extract_wheelchair_accessible_hotel(self):
        """Test extracting wheelchair accessible amenity from hotel."""
        hotel_property = {
            "name": "Accessible Hotel",
            "amenities": [
                {"id": 1, "name": "WiFi"},
                {"id": 53, "name": "Wheelchair accessible"},
                {"id": 5, "name": "Parking"},
            ],
        }
        accessibility = extract_hotel_accessibility(hotel_property)
        assert accessibility["wheelchair_accessible"] is True
        assert accessibility["accessible_room_available"] is True
        assert accessibility["wheelchair_amenity_id"] == 53

    def test_extract_non_wheelchair_hotel(self):
        """Test hotel without wheelchair accessibility."""
        hotel_property = {
            "name": "Standard Hotel",
            "amenities": [{"id": 1, "name": "WiFi"}, {"id": 5, "name": "Parking"}],
        }
        accessibility = extract_hotel_accessibility(hotel_property)
        assert accessibility["wheelchair_accessible"] is False
        assert accessibility["accessible_room_available"] is False

    def test_extract_hotel_without_amenities(self):
        """Test hotel with no amenities field."""
        hotel_property = {"name": "Simple Hotel"}
        accessibility = extract_hotel_accessibility(hotel_property)
        assert accessibility["wheelchair_accessible"] is False
        assert accessibility["wheelchair_amenity_id"] == 53

    def test_extract_hotel_empty_amenities(self):
        """Test hotel with empty amenities list."""
        hotel_property = {"name": "Empty Hotel", "amenities": []}
        accessibility = extract_hotel_accessibility(hotel_property)
        assert accessibility["wheelchair_accessible"] is False

    def test_extract_hotel_malformed_amenities(self):
        """Test hotel with malformed amenities."""
        hotel_property = {
            "name": "Malformed Hotel",
            "amenities": [
                "WiFi",  # String instead of dict
                {"id": 53},  # Valid
                None,  # None value
            ],
        }
        accessibility = extract_hotel_accessibility(hotel_property)
        assert accessibility["wheelchair_accessible"] is True


class TestAmadeusHotelAccessibilityExtraction:
    """Test extraction of accessibility data from Amadeus hotels."""

    def test_extract_amadeus_accessible_facilities(self):
        """Test extracting accessibility from Amadeus facilities."""
        hotel_data = {
            "name": "Accessible Hotel",
            "facilities": [
                {"description": "Wheelchair accessible rooms"},
                {"description": "Accessible bathroom with grab bars"},
                {"description": "Elevator"},
                {"description": "Accessible parking"},
            ],
        }
        accessibility = extract_amadeus_hotel_accessibility(hotel_data)
        assert accessibility["wheelchair_accessible"] is True
        assert accessibility["accessible_room_available"] is True
        assert len(accessibility["facility_list"]) == 4

    def test_extract_amadeus_no_accessibility(self):
        """Test Amadeus hotel without accessibility features."""
        hotel_data = {
            "name": "Standard Hotel",
            "facilities": [
                {"description": "WiFi"},
                {"description": "Restaurant"},
                {"description": "Gym"},
            ],
        }
        accessibility = extract_amadeus_hotel_accessibility(hotel_data)
        assert accessibility["wheelchair_accessible"] is False

    def test_extract_amadeus_no_facilities(self):
        """Test Amadeus hotel with no facilities."""
        hotel_data = {"name": "Simple Hotel"}
        accessibility = extract_amadeus_hotel_accessibility(hotel_data)
        assert accessibility["wheelchair_accessible"] is False
        assert accessibility["facility_list"] == []

    def test_extract_amadeus_accessibility_keywords(self):
        """Test detection of various accessibility keywords."""
        keywords = [
            "wheelchair",
            "accessible",
            "mobility",
            "elevator",
            "ramp",
            "parking",
            "bathroom",
        ]

        for keyword in keywords:
            hotel_data = {
                "facilities": [{"description": f"Feature with {keyword} available"}]
            }
            accessibility = extract_amadeus_hotel_accessibility(hotel_data)
            assert accessibility["wheelchair_accessible"] is True, (
                f"Failed for keyword: {keyword}"
            )

    def test_extract_amadeus_case_insensitive(self):
        """Test that accessibility keyword matching is case-insensitive."""
        hotel_data = {
            "facilities": [
                {"description": "WHEELCHAIR ACCESSIBLE ROOMS"},
                {"description": "Accessible BATHROOM"},
            ]
        }
        accessibility = extract_amadeus_hotel_accessibility(hotel_data)
        assert accessibility["wheelchair_accessible"] is True


# =====================================================================
# FLIGHT ACCESSIBILITY EXTRACTION TESTS
# =====================================================================


class TestFlightAccessibilityExtraction:
    """Test extraction of accessibility data from flight offers."""

    def test_extract_flight_basic(self):
        """Test basic flight accessibility extraction."""
        flight_offer = {
            "id": "1",
            "source": "GDS",
            "instantTicketingRequired": False,
            "nonHomogeneous": False,
            "oneWay": False,
            "lastTicketingDate": "2025-02-20",
            "numberOfBookableSeats": 4,
            "itineraries": [],
        }
        accessibility = extract_flight_accessibility_from_amadeus(flight_offer)
        assert accessibility["wheelchair_available"] is False
        assert accessibility["accessible_lavatory"] is False
        assert accessibility["notes"] is not None

    def test_extract_flight_with_notes(self):
        """Test that extraction includes helpful notes."""
        flight_offer = {}
        accessibility = extract_flight_accessibility_from_amadeus(flight_offer)
        assert "Check with airline" in accessibility["notes"]

    def test_extract_flight_default_values(self):
        """Test that all fields have default values."""
        flight_offer = {}
        accessibility = extract_flight_accessibility_from_amadeus(flight_offer)
        assert "wheelchair_available" in accessibility
        assert "wheelchair_stowage" in accessibility
        assert "accessible_lavatory" in accessibility
        assert "extra_legroom_available" in accessibility
        assert "special_service_codes" in accessibility
        assert "companion_required" in accessibility
        assert "special_meals_available" in accessibility
        assert "notes" in accessibility


# =====================================================================
# ACCESSIBILITY REQUEST MODEL TESTS
# =====================================================================


class TestAccessibilityRequestCreation:
    """Test creating accessibility requests for trip planning."""

    def test_request_for_wheelchair_user(self):
        """Test creating accessibility request for wheelchair user."""
        request = AccessibilityRequest(
            wheelchair_user=True,
            special_requirements="Manual wheelchair, needs accessible bathroom",
        )
        assert request.wheelchair_user is True
        assert "wheelchair" in request.special_requirements.lower()

    def test_request_for_deaf_traveler(self):
        """Test creating accessibility request for deaf traveler."""
        request = AccessibilityRequest(
            deaf=True,
            special_requirements="Visual alerts needed, no audio announcements",
        )
        assert request.deaf is True
        assert request.blind is False

    def test_request_for_blind_traveler(self):
        """Test creating accessibility request for blind traveler."""
        request = AccessibilityRequest(
            blind=True, special_requirements="Braille and audio guide needed"
        )
        assert request.blind is True
        assert request.deaf is False

    def test_request_for_multiple_disabilities(self):
        """Test accessibility request with multiple disabilities."""
        request = AccessibilityRequest(
            wheelchair_user=True,
            reduced_mobility=True,
            companion_required=True,
            special_requirements="Needs both wheelchair and assistance",
        )
        assert request.wheelchair_user is True
        assert request.reduced_mobility is True
        assert request.companion_required is True

    def test_request_for_stretcher_case(self):
        """Test accessibility request for medical case."""
        request = AccessibilityRequest(
            stretcher_case=True,
            companion_required=True,
            special_requirements="Requires medical oxygen and constant monitoring",
        )
        assert request.stretcher_case is True
        assert request.companion_required is True


# =====================================================================
# INTEGRATED ACCESSIBILITY SCENARIO TESTS
# =====================================================================


class TestAccessibilityScenarios:
    """Test realistic accessibility scenarios."""

    def test_wheelchair_user_hotel_search_scenario(self):
        """Test filtering hotels for wheelchair user."""
        # Simulate hotel search results
        hotels = [
            {
                "name": "Luxury Hotel",
                "amenities": [
                    {"id": 1, "name": "WiFi"},
                    {"id": 53, "name": "Wheelchair accessible"},
                ],
            },
            {"name": "Budget Hotel", "amenities": [{"id": 1, "name": "WiFi"}]},
            {
                "name": "Accessible Inn",
                "amenities": [
                    {"id": 53, "name": "Wheelchair accessible"},
                    {"id": 5, "name": "Parking"},
                ],
            },
        ]

        # Extract accessibility for each hotel
        accessible_hotels = []
        for hotel in hotels:
            accessibility = extract_hotel_accessibility(hotel)
            if accessibility["wheelchair_accessible"]:
                accessible_hotels.append(hotel["name"])

        assert len(accessible_hotels) == 2
        assert "Luxury Hotel" in accessible_hotels
        assert "Accessible Inn" in accessible_hotels

    def test_deaf_traveler_flight_search_scenario(self):
        """Test flight accessibility info for deaf traveler."""
        request = AccessibilityRequest(
            deaf=True,
            special_requirements="Needs visual alerts, no audio announcements",
        )

        # Simulate flight search
        flight = {}
        accessibility = extract_flight_accessibility_from_amadeus(flight)

        # Should have notes about contacting airline
        assert accessibility["notes"] is not None
        assert "airline" in accessibility["notes"].lower()

    def test_complex_accessibility_requirements(self):
        """Test handling complex accessibility requirements."""
        request = AccessibilityRequest(
            wheelchair_user=True,
            deaf=True,
            companion_required=True,
            special_requirements="Wheelchair user who is deaf, needs both visual alerts and accessible facilities, traveling with companion",
        )

        # Verify all accessibility needs are captured
        assert request.wheelchair_user is True
        assert request.deaf is True
        assert request.companion_required is True
        assert len(request.special_requirements) > 0


# =====================================================================
# ACCESSIBILITY DATA VALIDATION TESTS
# =====================================================================


class TestAccessibilityDataValidation:
    """Test validation of accessibility data structures."""

    def test_flight_accessibility_schema(self):
        """Test that FlightAccessibility has valid schema."""
        accessibility = FlightAccessibility(
            wheelchair_available=True, special_service_codes=["WCHR", "WCHS"]
        )
        # Validate schema
        schema = FlightAccessibility.model_json_schema()
        assert "properties" in schema
        assert "special_service_codes" in schema["properties"]

    def test_hotel_accessibility_schema(self):
        """Test that HotelAccessibility has valid schema."""
        accessibility = HotelAccessibility(
            wheelchair_accessible=True,
            facility_list=["Roll-in shower", "Accessible parking"],
        )
        schema = HotelAccessibility.model_json_schema()
        assert "properties" in schema
        assert "facility_list" in schema["properties"]

    def test_accessibility_request_schema(self):
        """Test that AccessibilityRequest has valid schema."""
        request = AccessibilityRequest(wheelchair_user=True, deaf=True)
        schema = AccessibilityRequest.model_json_schema()
        assert "properties" in schema
        assert "wheelchair_user" in schema["properties"]
        assert "deaf" in schema["properties"]

    def test_accessibility_models_serialization(self):
        """Test that accessibility models can be serialized."""
        accessibility = HotelAccessibility(
            wheelchair_accessible=True,
            accessible_parking=True,
            facility_list=["Wheelchair accessible", "Accessible parking"],
        )
        # Should be serializable to JSON
        json_data = accessibility.model_dump_json()
        assert json_data is not None
        assert "wheelchair_accessible" in json_data

    def test_accessibility_models_deserialization(self):
        """Test that accessibility models can be deserialized."""
        data = {
            "wheelchair_accessible": True,
            "accessible_room_available": True,
            "wheelchair_amenity_id": 53,
            "facility_list": ["Wheelchair accessible"],
        }
        accessibility = HotelAccessibility(**data)
        assert accessibility.wheelchair_accessible is True
        assert accessibility.facility_list == ["Wheelchair accessible"]
