# 🌟 MCP Travel Concierge Server

> **The Ultimate AI Travel Planning Assistant** - A comprehensive MCP (Model
> Context Protocol) server that combines the best of Google Travel Services with
> Amadeus Professional Systems.

## 🚀 Overview

This Travel Concierge Server integrates **two powerful travel platforms** into
one comprehensive solution:

- 🌐 **Google Travel Services** (via SerpAPI) - Consumer-friendly search across
  flights, hotels, and events
- 🏢 **Amadeus Global Distribution System** - Professional travel industry
  inventory and pricing

<div>
    <a href="https://www.loom.com/share/f865f975724b441fb31d88e20aa23067">
      <p>MCP AI TRAVEL ASSISTANT - Watch Video</p>
    </a>
    <a href="https://www.loom.com/share/f865f975724b441fb31d88e20aa23067">
      <img style="max-width:300px;" src="https://cdn.loom.com/sessions/thumbnails/f865f975724b441fb31d88e20aa23067-488994d5a959c3ff-full-play.gif">
    </a>
  </div>

Get the **best of both worlds**: consumer accessibility with professional depth!

## ✨ Key Features

### ✈️ Dual Flight Search

- **Google Flights**: Consumer-friendly pricing, popular routes, price insights
- **Amadeus GDS**: Professional airline inventory, detailed fare classes,
  real-time availability

### 🏨 Comprehensive Hotel Search

- **Google Hotels**: Vacation rentals, boutique properties, consumer reviews
- **Amadeus Hotels**: Professional rates, real-time availability, business
  travel optimization

### 🎭 Complete Event & Activity Discovery

- **Google Events**: Local festivals, concerts, cultural events
- **Amadeus Activities**: Professional tours, curated experiences, verified
  operators

### 🌍 Additional Services

- **Geocoding & Distance Calculation**: Precise location services
- **Weather Intelligence**: Real-time conditions and forecasts
- **Currency Conversion**: Live exchange rates

## 🇨🇭 Swiss Travel Ecosystem

This server is part of a **federated MCP ecosystem** for comprehensive Swiss travel planning. For Switzerland trips, configure these companion MCP servers for specialized capabilities:

### Companion Servers

| Server | Focus | Tools | Highlights |
|--------|-------|-------|-----------|
| **journey-service-mcp** | Swiss rail planning | 8 tools | Real-time SBB, 126+ stations, ♿ wheelchair routing, 🌍 CO2 tracking |
| **swiss-mobility-mcp** | Rail ticketing | 8 tools | SBB pricing, booking, GA pass, PDF tickets |
| **swiss-tourism-mcp** | Attractions & packages | 21 tools | 283 sights, 133 RailAway combos, ♿ accessible attractions |
| **open-meteo-mcp** | Weather intelligence | 11 tools | 16-day forecasts, snow, pollen, air quality, comfort index |

### ♿ Accessibility-First Travel Planning

Our ecosystem prioritizes **inclusive travel** for all abilities:

**Journey Service MCP:**
- Wheelchair-accessible route planning with 4 accessibility levels
  - Self-boarding, crew assistance, notification-required, shuttle-transport
- Train accessibility data: wheelchair spaces, accessible toilets, visual aids
- Optimized transfer times for mobility-restricted travelers (10+ min minimum)
- Real-time platform accessibility information

**Swiss Tourism MCP:**
- Barrier-free attraction filtering: wheelchair, mobility, pet-friendly, stroller-compatible
- Comprehensive accessible tourism prompt covering:
  - Wheelchair-accessible attractions and accommodations
  - Level boarding and accessible transport connections
  - Hotels with roll-in showers and accessible bathrooms
  - Sensory, cognitive, dietary, and medical needs
  - Accessible parking and resting areas

### 🌍 Ecology-Conscious Travel Planning

Our ecosystem promotes **sustainable, low-carbon travel**:

**Journey Service MCP:**
- CO2 emissions analysis comparing train vs car vs plane
- Eco-friendly route recommendations with tree offset calculations
- Train-based travel (lowest carbon footprint for ground transport)

**Open-Meteo MCP:**
- Air quality monitoring: CO, NO₂, SO₂, O₃ levels
- Pollen data for health-conscious travel planning
- Weather alerts for activity safety

**Travel Concierge Server:**
- Currency conversion for budget-conscious planning
- Supports rail+attraction RailAway combo packages (efficient travel)

### Orchestration Example

```
User: "Plan a 3-day ski trip to Zermatt"

Claude orchestrates across servers:
1. meteo__get_snow_conditions() → Check resort snow/weather
2. tourism__search_resorts() → Find ski resorts
3. journey__find_trips() → Plan train Zurich → Zermatt
4. mobility__get_trip_pricing() → Calculate rail ticket cost
5. search_hotels_serpapi() → Find alpine lodging (this server)
6. meteo__get_weather() → Get 3-day forecast
7. convert_currency() → CHF pricing (this server)

Result: Complete ski trip plan with rail, accommodation, weather, pricing
```

### Setup Federation

Add all servers to your Claude Desktop config:

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

Claude automatically orchestrates across all servers for Swiss travel planning.

## 🛠️ Installation & Setup

### 1. Clone and Install Dependencies

```bash
# Clone the repository
git clone https://github.com/your-username/mcp_travelassistant.git
cd mcp_travelassistant

# Install dependencies
pip install -r requirements.txt
```

### 2. Set Up Environment Variables

Create a `.env` file in the project root with your API keys:

```bash
# Copy the example environment file
cp env.example .env
```

Edit the `.env` file with your actual API keys:

```env
# Required API Keys
SERPAPI_KEY=your_serpapi_key_here
AMADEUS_API_KEY=your_amadeus_api_key_here
AMADEUS_API_SECRET=your_amadeus_api_secret_here
EXCHANGE_RATE_API_KEY=your_exchange_rate_api_key_here
```

**Where to get API keys:**

- **SERPAPI_KEY**: Get from [SerpAPI](https://serpapi.com/)
- **AMADEUS_API_KEY** & **AMADEUS_API_SECRET**: Get from
  [Amadeus for Developers](https://developers.amadeus.com/)
- **EXCHANGE_RATE_API_KEY**: Get from
  [ExchangeRate-API](https://exchangerate-api.com/)

### 3. Run the Server

```bash
python travel_server.py
```

## 🔧 MCP Configuration

### For Claude Desktop

Add this configuration to your Claude Desktop config file (usually located at
`~/.cursor/mcp.json` or
`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "travel-concierge": {
      "command": "python",
      "args": ["combined_travel_server.py"],
      "cwd": "/path/to/your/mcp_travelassistant",
      "env": {
        "SERPAPI_KEY": "your_serpapi_key_here",
        "AMADEUS_API_KEY": "your_amadeus_api_key_here",
        "AMADEUS_API_SECRET": "your_amadeus_api_secret_here",
        "EXCHANGE_RATE_API_KEY": "your_exchange_rate_api_key_here"
      }
    }
  }
}
```

### For UV Package Manager

If you're using UV, you can use this configuration:

```json
{
  "mcpServers": {
    "travel-concierge": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/your/mcp_travelassistant/",
        "run",
        "python",
        "combined_travel_server.py"
      ],
      "env": {
        "SERPAPI_KEY": "your_serpapi_key_here",
        "AMADEUS_API_KEY": "your_amadeus_api_key_here",
        "AMADEUS_API_SECRET": "your_amadeus_api_secret_here",
        "EXCHANGE_RATE_API_KEY": "your_exchange_rate_api_key_here"
      }
    }
  }
}
```

### For HTTP Mode

If you prefer running the server in HTTP mode:

```json
{
  "mcpServers": {
    "travel-concierge": {
      "command": "npx",
      "args": ["@modelcontextprotocol/client-http", "http://localhost:8000/"]
    }
  }
}
```

Then run the server with: `python travel_server.py --transport http --port 8000`

## 🎯 Available Tools

### ✈️ Flight Search Tools

| Tool                       | Provider       | Description                                |
| -------------------------- | -------------- | ------------------------------------------ |
| `search_flights_serpapi()` | Google Flights | Consumer flight search with price insights |
| `search_flights_amadeus()` | Amadeus GDS    | Professional airline inventory and fares   |

### 🏨 Hotel Search Tools

| Tool                                 | Provider      | Description                              |
| ------------------------------------ | ------------- | ---------------------------------------- |
| `search_hotels_serpapi()`            | Google Hotels | Consumer hotel search with reviews       |
| `search_hotels_amadeus_by_city()`    | Amadeus GDS   | Professional city-based hotel search     |
| `search_hotels_amadeus_by_geocode()` | Amadeus GDS   | Professional coordinate-based search     |
| `search_hotel_offers_amadeus()`      | Amadeus GDS   | Real-time hotel availability and pricing |

### 🎭 Event & Activity Tools

| Tool                          | Provider      | Description                           |
| ----------------------------- | ------------- | ------------------------------------- |
| `search_events_serpapi()`     | Google Events | Local events and cultural experiences |
| `search_activities_amadeus()` | Amadeus GDS   | Professional tours and activities     |

### 🌍 Utility Tools

| Tool                       | Provider         | Description                           |
| -------------------------- | ---------------- | ------------------------------------- |
| `geocode_location()`       | Nominatim        | Convert addresses to coordinates      |
| `calculate_distance()`     | Geopy            | Calculate distances between locations |
| `get_weather_forecast()`   | Open-Meteo       | Weather forecasts for travel planning |
| `get_current_conditions()` | Open-Meteo       | Real-time weather conditions          |
| `convert_currency()`       | ExchangeRate-API | Live currency conversion              |

## 🎨 Usage Examples

### Comprehensive Trip Planning

```python
# Search for flights from multiple providers
google_flights = search_flights_serpapi(
    departure_id="JFK",
    arrival_id="CDG",
    outbound_date="2025-06-15",
    return_date="2025-06-22",
    adults=2
)

amadeus_flights = search_flights_amadeus(
    originLocationCode="JFK",
    destinationLocationCode="CDG",
    departureDate="2025-06-15",
    returnDate="2025-06-22",
    adults=2
)
```

### Hotel Search Strategy

```python
# Get coordinates first
location = geocode_location("Paris city center")

# Consumer search via Google Hotels
google_hotels = search_hotels_serpapi(
    location="Paris city center",
    check_in_date="2025-06-15",
    check_out_date="2025-06-22"
)

# Professional search via Amadeus
amadeus_hotels = search_hotel_offers_amadeus(
    cityCode="PAR",
    checkInDate="2025-06-15",
    checkOutDate="2025-06-22"
)
```

### Complete Trip Planning

```python
# 1. Get destination coordinates
coords = geocode_location("Paris, France")

# 2. Check weather
weather = get_weather_forecast(
    latitude=coords['latitude'],
    longitude=coords['longitude']
)

# 3. Find events
events = search_events_serpapi(
    query="concerts museums",
    location="Paris",
    date_filter="week"
)

# 4. Convert currency for budget planning
budget_eur = convert_currency(
    from_currency="USD",
    to_currency="EUR",
    amount=2000
)
```

## 🌟 Best Practices

### 1. **Dual Search Strategy**

Always search both platforms for flights and hotels to ensure you get the best
deals and comprehensive options.

### 2. **Location First**

Start with `geocode_location()` to get precise coordinates, then use those for
location-based searches.

### 3. **Weather Integration**

Check weather forecasts before finalizing activity plans using
`get_weather_forecast()`.

### 4. **Currency Planning**

Use `convert_currency()` for accurate international travel budgeting.

## 🔄 Docker Support

### Build and Run

```bash
# Build the Docker image
docker build -t travel-concierge .

# Run with environment variables
docker run -p 8000:8000 \
  -e SERPAPI_KEY=your_key \
  -e AMADEUS_API_KEY=your_key \
  -e AMADEUS_API_SECRET=your_secret \
  -e EXCHANGE_RATE_API_KEY=your_key \
  travel-concierge
```

### Docker Compose

```bash
# Copy environment file
cp env.example .env

# Edit .env with your API keys
# Then run:
docker-compose up
```

## 🧪 Testing

The project includes a comprehensive test suite with **126 passing tests** and **52% code coverage**.

```bash
# Run all tests
uv run pytest tests/ -v

# Run with coverage report
uv run pytest tests/ --cov=src/travel_assistant --cov-report=term-missing

# Run specific test file
uv run pytest tests/test_models.py -v
```

**Coverage Breakdown:**
- `models.py`: 99% coverage
- `clients.py`: 75% coverage
- `helpers.py`: 73% coverage
- `__init__.py`: 100% coverage
- `server.py`: 16% coverage (tool implementations require async integration testing)

## 🐛 Troubleshooting

### Common Issues

1. **Missing API Keys**

   ```
   Error: SERPAPI_KEY environment variable is required
   ```

   Solution: Set your API keys in the `.env` file or environment variables

2. **Port Already in Use**

   ```
   Error: Port 8000 is already in use
   ```

   Solution: Use a different port with `--port 8001`

3. **Amadeus Authentication Error**

   ```
   Error: Invalid API credentials
   ```

   Solution: Verify your Amadeus API key and secret are correct

### Health Check

When running in HTTP mode, visit `http://localhost:8000/health` to verify the
server is running properly.

## 📈 Performance

- **Unified Architecture**: Single server reduces overhead and complexity
- **Concurrent Requests**: Handles multiple simultaneous requests efficiently
- **Rate Limiting**: Built-in rate limiting for external API calls
- **Error Handling**: Comprehensive error handling and recovery

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests if applicable
5. Commit your changes (`git commit -m 'Add some amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file
for details.

## 🙏 Acknowledgments

- **Amadeus for Developers** - Professional travel industry data
- **SerpAPI** - Google Services integration
- **Open-Meteo** - Weather data services
- **ExchangeRate-API** - Currency conversion services
- **Nominatim/OpenStreetMap** - Geocoding services

## 🆘 Support

For support, please:

1. Check the documentation above
2. Review the example environment file
3. Open an issue with detailed information about your problem

---

**Happy Travels!** ✈️🏨🎭🌍
