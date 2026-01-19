"""FastMCP server entry point - allows running as: python -m travel_assistant"""

from travel_assistant.server import mcp

if __name__ == "__main__":
    mcp.run()
