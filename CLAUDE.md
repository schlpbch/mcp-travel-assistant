# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Travel Assistant MCP Server** (v2.0) - A comprehensive Model Context Protocol server providing unified travel planning by combining Google Travel Services (via SerpAPI) with Amadeus Global Distribution System (professional travel industry inventory). The server exposes 20+ tools for flights, hotels, events, activities, location services, weather, currency conversion, and financial tracking.

**Architecture Style:** Modular multi-file (aligned with open-meteo-mcp), FastMCP 2.0, using Pydantic for type safety.

## Repository Structure

```
travel-assistant/
├── src/travel_assistant/           # Main package (src-layout)
│   ├── __init__.py                # Package metadata (__version__ = "2.0.0")
│   ├── server.py                  # MCP server, tools, resources, prompts
│   ├── clients.py                 # API client classes (SerpAPI, Amadeus, etc.)
│   ├── models.py                  # Pydantic models for type safety
│   ├── helpers.py                 # Utility functions (geocoding, API keys, etc.)
│   └── data/                      # Static JSON data files
├── tests/                         # Test suite (pytest)
├── server.py                      # Root entry point wrapper
├── pyproject.toml                # Project config (hatchling build system)
├── uv.lock                        # Dependency lock file (reproducible builds)
├── .python-version               # Python 3.11 pinning
├── Dockerfile                     # Container configuration
├── docker-compose.yml             # Compose orchestration
├── env.example                    # Environment variable template
├── README.md                      # User documentation
└── CLAUDE.md                      # This file
```

## Core Architecture

### 1. **server.py** (1522 lines)
Located at: `src/travel_assistant/server.py`

Contains:
- **FastMCP 2.0 initialization** (no `dependencies` parameter)
- **AppContext & lifespan** - Manages Amadeus client lifecycle (runs once per server in v2.0)
- **20 MCP tools** organized in 6 functional sections:
  - ✈️ Flights: `search_flights_serpapi`, `search_flights_amadeus`
  - 🏨 Hotels: `search_hotels_serpapi`, `search_hotels_amadeus_by_city`, `search_hotels_amadeus_geocode`, `search_hotel_offers_amadeus`
  - 🎭 Events: `search_events_serpapi`, `search_activities_amadeus`, `get_activity_details_amadeus`
  - 🌍 Geocoding: `geocode_location`, `calculate_distance`
  - 🌦️ Weather: `get_current_conditions`, `get_weather_forecast`
  - 💰 Finance: `convert_currency`, `lookup_stock`
- **1 MCP Prompt** - `travel_planning_prompt()` with structured planning guidance
- **1 MCP Resource** - `combined_travel_server_capabilities()` with detailed documentation

### 2. **clients.py** (~400 lines)
Located at: `src/travel_assistant/clients.py`

API client wrapper classes:
- **SerpAPIClient** - Google Flights, Hotels, Events, Finance via SerpAPI
- **AmadeusClientWrapper** - Wraps Amadeus SDK with validation and error handling
- **ExchangeRateClient** - Currency conversion via ExchangeRate-API
- **OpenMeteoClient** - Weather forecasts and current conditions
- **GeocodingClient** - Nominatim geocoding with rate limiting

All clients encapsulate API logic and validation, returning dicts/JSON with consistent error handling.

### 3. **models.py** (~240 lines)
Located at: `src/travel_assistant/models.py`

**Pydantic models for type safety and validation:**

Data Models:
- **AppContext** - Dataclass for lifespan context (Amadeus client)
- **Parameter Models**: FlightSearchParams, AmadeusFlightSearchParams, HotelSearchParams, EventSearchParams, etc.
- **Response Models**: FlightResult, HotelResult, WeatherForecast, GeocodeResult, CurrencyConversion, etc.
- **All fields include Field() descriptions** for auto-documentation

Benefits:
- Type validation at runtime
- Auto-documentation for tools
- IDE autocomplete support
- Structured error messages

### 4. **helpers.py** (~50 lines)
Located at: `src/travel_assistant/helpers.py`

Utility functions:
- `get_serpapi_key()` - Retrieve SERPAPI_KEY environment variable
- `get_exchange_rate_api_key()` - Retrieve EXCHANGE_RATE_API_KEY
- `get_geolocator()` - Initialize Nominatim geocoder with rate limiting
- `get_nws_headers()` - HTTP headers for NWS API requests
- `make_nws_request()` - Generic request helper with error handling

### 5. **__init__.py** (~3 lines)
Located at: `src/travel_assistant/__init__.py`

Package initialization:
```python
"""Travel Assistant MCP Server - A comprehensive travel planning service."""
__version__ = "2.0.0"
```

### 6. **server.py** (root entry point, ~5 lines)
Located at: `/server.py`

Simple wrapper that imports and runs the server:
```python
from travel_assistant.server import mcp
if __name__ == "__main__":
    mcp.run()
```

## Development Workflow

### Running the Server

```bash
# Using uv (recommended)
uv run python server.py                              # Stdio mode (MCP default)
uv run python server.py --transport http --port 8000  # HTTP mode for testing

# Using docker
docker build -t travel-assistant .
docker run -e SERPAPI_KEY=... -e AMADEUS_API_KEY=... travel-assistant

# Using docker-compose
docker-compose up
```

### Development Commands

```bash
# Install/sync dependencies
uv sync                    # Create/update virtual environment and uv.lock

# Run tests (when implemented)
uv run pytest

# Type checking
uv run mypy src/travel_assistant

# Formatting/linting
uv run black src/
uv run isort src/
uv run flake8 src/
```

### Environment Variables Required

See `env.example` for the complete template:
```bash
SERPAPI_KEY=your_key_here
AMADEUS_API_KEY=your_key_here
AMADEUS_API_SECRET=your_secret_here
EXCHANGE_RATE_API_KEY=your_key_here
```

## Key Design Patterns

### Dual-Provider Strategy
- Each major travel function (flights, hotels, events) has both:
  - **Consumer-friendly provider** (SerpAPI → Google services)
  - **Professional provider** (Amadeus GDS for travel industry data)
- Tools documented to use both for comprehensive results

### Context Injection (FastMCP 2.0)
```python
@mcp.tool()
def search_flights_amadeus(
    ...params...,
    ctx: Context  # ← Injected by FastMCP
) -> str:
    amadeus_client = ctx.request_context.lifespan_context.amadeus_client
```

### Error Handling
All tools return error dicts instead of raising exceptions:
```python
try:
    # API call
    return {"result": data}
except Exception as e:
    return {"error": f"Description: {str(e)}"}
```

### Response Consistency
- SerpAPI tools return **Dict[str, Any]**
- Amadeus tools return **JSON string** (via json.dumps)
- All include `provider` and `search_timestamp` fields

## Testing

Test infrastructure is configured but no tests yet implemented. When adding tests:

```bash
# Create tests/ directory with pytest files
# Example: tests/test_clients.py, tests/test_models.py, tests/test_server.py

uv run pytest                           # Run all tests
uv run pytest --cov=src/travel_assistant  # With coverage
```

Configuration in `pyproject.toml`:
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = ["test_*.py"]
```

## FastMCP 2.0 Migration Notes

**Breaking changes made:**
- ✅ Import: `from mcp.server.fastmcp` → `from fastmcp`
- ✅ Removed: `dependencies=["amadeus", "requests", "geopy"]` parameter (line 46)
- ✅ Updated: `fastmcp>=0.1.0` → `fastmcp>=2.0.0,<3.0.0` in pyproject.toml

**Behavioral improvements:**
- Lifespan now runs once per server (not per session) → Amadeus client shared across requests
- Better error handling and logging
- Improved async/await support

**No changes needed for:**
- Decorator syntax (`@mcp.tool()`, `@mcp.prompt()`, `@mcp.resource()`)
- Context methods (`ctx.info()`, etc.)
- Tool implementations
- Type hints

## Build System & Packaging

**Current (v2.0):**
- Build: hatchling (modern, auto-detects src-layout)
- Packaging: pyproject.toml (PEP 517/518 compliant)
- Dependency management: uv (fast, reproducible)
- Lock file: uv.lock (2071 lines, checked in)

**Installation:**
```bash
uv pip install -e .          # Editable install (development)
uv pip install travel-assistant  # From package
```

## Dependencies

**Core dependencies:**
- fastmcp>=2.0.0 - MCP server framework
- amadeus>=12.0.0 - Professional travel data API
- requests>=2.31.0 - HTTP requests
- geopy>=2.3.0 - Geocoding (Nominatim)
- pydantic>=2.0.0 - Data validation
- python-dotenv>=1.0.1 - Environment variables

**Optional (dev):**
- pytest, pytest-asyncio - Testing
- black, isort, flake8 - Code formatting/linting

## Common Tasks

### Adding a New Tool

1. Design Pydantic parameters and response models in `models.py`
2. Add implementation function in `server.py` or extract to client in `clients.py`
3. Decorate with `@mcp.tool()`
4. Write comprehensive docstring with description and arg explanations
5. Include error handling (return error dict, don't raise)
6. Update `combined_travel_server_capabilities()` resource

### Modifying an API Client

1. Edit class in `clients.py`
2. Update Pydantic models in `models.py` if parameters/responses changed
3. Ensure backward compatibility or update tool implementations
4. Test with `uv run pytest` or manual testing

### Adding Environment Variables

1. Add to `env.example`
2. Create getter function in `helpers.py` (e.g., `get_my_api_key()`)
3. Import and use in appropriate client or tool
4. Document in README.md

## Useful File Paths

| File | Purpose |
|------|---------|
| `src/travel_assistant/server.py:16` | FastMCP 2.0 import |
| `src/travel_assistant/server.py:46` | FastMCP initialization (no dependencies param) |
| `src/travel_assistant/server.py:93-1219` | All 20 tool definitions |
| `src/travel_assistant/server.py:1225` | travel_planning_prompt |
| `src/travel_assistant/server.py:1330` | combined_travel_server_capabilities resource |
| `src/travel_assistant/clients.py` | All API client wrappers |
| `src/travel_assistant/models.py` | All Pydantic models |
| `src/travel_assistant/helpers.py` | Utility functions |
| `pyproject.toml:26` | FastMCP dependency version |
| `pyproject.toml:59-65` | Pytest configuration |
| `uv.lock` | Reproducible dependency lock file |

## Testing

### Test Suite Overview

The project includes a comprehensive test suite with **126 passing tests** covering all major components:

```
tests/
├── test_helpers.py        # 10 tests: API keys, geolocator, NWS requests (100% coverage)
├── test_models.py         # 51 tests: Pydantic model validation (100% coverage)
├── test_clients.py        # 39 tests: API client mocking with responses library (77% coverage)
├── test_server.py         # 26 tests: Server structure and integration (13% coverage)
├── conftest.py            # Shared fixtures (autouse mock env vars)
└── __init__.py            # Package marker
```

### Running Tests

```bash
# Run all tests with verbose output
uv run pytest tests/ -v

# Run with coverage report
uv run pytest tests/ --cov=src/travel_assistant --cov-report=html --cov-report=term-missing

# Run specific test file
uv run pytest tests/test_models.py -v

# Run specific test class
uv run pytest tests/test_clients.py::TestSerpAPIClient -v

# Run with output capture disabled
uv run pytest tests/ -v -s
```

### Coverage Summary

| Module | Coverage | Lines |
|--------|----------|-------|
| `helpers.py` | 100% | 30 |
| `models.py` | 100% | 147 |
| `clients.py` | 77% | 191 |
| `server.py` | 13% | 483 |
| **Overall** | **45%** | **852** |

*Note: Low server.py coverage is expected - it contains mostly tool handler functions that require async MCP client testing beyond unit scope.*

### Test Organization

**1. test_helpers.py** - Utility function tests
- API key retrieval with monkeypatch
- Geolocator rate limiter verification
- NWS request header validation
- HTTP error handling (500, 404, timeouts)

**2. test_models.py** - Pydantic model validation
- Valid input creation for all 20+ models
- Default value verification
- Field constraint validation (ranges, required fields)
- Type validation (latitude/longitude bounds, currency amounts)

**3. test_clients.py** - API client mocking
- **SerpAPIClient**: Flight/hotel/event/stock searches with HTTP error handling
- **AmadeusClientWrapper**: Flight/hotel searches with parameter validation
- **ExchangeRateClient**: Currency conversion with API error handling
- **OpenMeteoClient**: Weather forecast and current conditions
- **GeocodingClient**: Geocoding and reverse geocoding with mocking

**4. test_server.py** - Server structure and integration
- FastMCP instance creation and properties
- Module import verification
- Client instantiation
- Server module structure validation

### Mocking Patterns Used

```python
# HTTP mocking with responses library
@responses.activate
def test_search_flights():
    responses.add(responses.GET, "https://serpapi.com/search",
                  json={"best_flights": []}, status=200)
    client = SerpAPIClient()
    result = client.search_flights(...)

# SDK mocking with unittest.mock
from unittest.mock import Mock
mock_amadeus = Mock()
mock_amadeus.shopping.flight_offers_search.get.return_value = mock_response
wrapper = AmadeusClientWrapper(mock_amadeus)

# Environment variable mocking
def test_api_key(monkeypatch):
    monkeypatch.setenv("SERPAPI_KEY", "test-key")
    assert get_serpapi_key() == "test-key"

# Conftest fixtures for shared setup
@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    # Automatically set env vars for all tests
    monkeypatch.setenv("SERPAPI_KEY", "test-serpapi-key-12345")
```

### Adding New Tests

1. **For new helpers**: Add to `test_helpers.py` using `@responses.activate` for HTTP
2. **For new models**: Add to `test_models.py` with valid/invalid data patterns
3. **For new clients**: Add to `test_clients.py` with `responses` mocking
4. **For server changes**: Update `test_server.py` integration tests

### Dependencies

Tests require dev dependencies (added via `uv pip install -e ".[dev]"`):
- `pytest>=8.0.0` - Test runner
- `pytest-asyncio>=0.23.0` - Async test support
- `pytest-cov>=4.1.0` - Coverage reports
- `responses>=0.25.0` - HTTP mocking for requests library

## Performance & Scalability

- **Lifespan management**: Amadeus client created once, shared across requests (FastMCP 2.0 improvement)
- **Rate limiting**: Nominatim geocoding uses rate limiter (1 req/sec min)
- **Timeout handling**: All API calls use 10s timeout
- **Error recovery**: Graceful error handling, returns error objects instead of raising
- **Modular design**: Easy to add new clients/tools without touching existing code

## Documentation

- **README.md** - User-facing documentation, setup, and examples
- **CLAUDE.md** - This file (developer guidance for Claude Code)
- **.cursorrules** (if added) - Cursor-specific rules for this project
- Inline docstrings on all tools with detailed parameter/return descriptions
- Pydantic Field descriptions auto-generate documentation

## Future Improvements

- ✅ **DONE**: Add comprehensive test suite in `tests/` (126 tests, 45% coverage)
- Extract repeated tool logic into helper functions (reduce server.py complexity)
- Consider asyncio refactoring for better performance
- Add monitoring/observability hooks
- Create task-specific prompts in addition to travel_planning_prompt
- Add CLI interface for local development
- Expand test coverage to include server tool integration tests
- Add property-based testing with hypothesis library

---

**Last Updated:** FastMCP 2.0 migration + modular refactoring (v2.0.0)
