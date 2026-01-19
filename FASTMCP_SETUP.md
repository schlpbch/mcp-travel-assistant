# FastMCP Server Setup & Configuration

## Quick Start

### 1. Install the Package

```bash
# Clone the repository
git clone https://github.com/schlpbch/mcp-travel-assistant
cd mcp-travel-assistant

# Install in editable mode (includes all dependencies)
uv pip install -e .
```

### 2. Configure Environment Variables

Create a `.env` file with your API keys:

```bash
SERPAPI_KEY=your_serpapi_key_here
AMADEUS_API_KEY=your_amadeus_key_here
AMADEUS_API_SECRET=your_amadeus_secret_here
EXCHANGE_RATE_API_KEY=your_exchangerate_key_here
```

### 3. Run the FastMCP Server

**Option A: Direct execution**
```bash
python server.py
```

**Option B: As Python module (recommended for FastMCP)**
```bash
python -m travel_assistant
```

**Option C: Using Docker**
```bash
docker build -t travel-assistant .
docker run -e SERPAPI_KEY=your_key \
           -e AMADEUS_API_KEY=your_key \
           -e AMADEUS_API_SECRET=your_secret \
           -e EXCHANGE_RATE_API_KEY=your_key \
           travel-assistant
```

## FastMCP Integration

### For Claude Code

Add to your Claude Code MCP config (`~/.claude/mcp-config.json` or via Claude Code settings):

```json
{
  "mcpServers": {
    "travel-assistant": {
      "command": "uv",
      "args": ["run", "--with", "travel-assistant", "python", "-m", "travel_assistant"],
      "env": {
        "SERPAPI_KEY": "your_key_here",
        "AMADEUS_API_KEY": "your_key_here",
        "AMADEUS_API_SECRET": "your_secret_here",
        "EXCHANGE_RATE_API_KEY": "your_key_here"
      }
    }
  }
}
```

### For Other MCP Clients

**Generic MCP config pattern:**
```json
{
  "mcpServers": {
    "travel-assistant": {
      "command": "python",
      "args": ["-m", "travel_assistant"],
      "env": {
        "SERPAPI_KEY": "${SERPAPI_KEY}",
        "AMADEUS_API_KEY": "${AMADEUS_API_KEY}",
        "AMADEUS_API_SECRET": "${AMADEUS_API_SECRET}",
        "EXCHANGE_RATE_API_KEY": "${EXCHANGE_RATE_API_KEY}"
      }
    }
  }
}
```

## Troubleshooting

### "No module named 'travel_assistant'"

**Solution:** The package must be installed first:
```bash
# Install globally
uv pip install -e /path/to/mcp-travel-assistant

# Or use uv with --with flag
uv run --with travel-assistant python -m travel_assistant
```

### "ImportError: cannot import name 'mcp' from 'travel_assistant.server'"

**Solution:** Verify the installation worked:
```bash
python -c "from travel_assistant.server import mcp; print('OK')"
```

### API Key Errors

**Solution:** Ensure all required environment variables are set:
```bash
env | grep -E "SERPAPI|AMADEUS|EXCHANGE"
```

## Testing the Server

```bash
# Run test suite
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ --cov=src/travel_assistant --cov-report=html
```

## Server Status

Check that the server started correctly:
```bash
# Should print server capabilities
python -c "from travel_assistant.server import mcp; print(f'Server: {mcp.name}'); print('Status: ✓ Ready')"
```

## Architecture

- **Entry point:** `server.py` (root) or `src/travel_assistant/__main__.py` (module)
- **MCP server:** `src/travel_assistant/server.py` (1,522 lines)
- **API clients:** `src/travel_assistant/clients.py` (390 lines)
- **Data models:** `src/travel_assistant/models.py` (240 lines)
- **Utilities:** `src/travel_assistant/helpers.py` (54 lines)

## Version

- **FastMCP:** >= 2.0.0
- **Python:** >= 3.10
- **Package:** v2.0.0

See [CLAUDE.md](./CLAUDE.md) for full developer documentation.
