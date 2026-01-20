#!/usr/bin/env python3
"""Detailed Travel Concierge Server Analysis"""

import sys
sys.path.insert(0, '/home/schlpbch/code/mcp-travel-assistant/src')

def analyze_server():
    """Analyze the Travel Concierge MCP Server"""
    print("🔍 Travel Concierge MCP Server - Detailed Analysis")
    print("=" * 60)
    
    try:
        from travel_assistant.server import mcp
        
        # Get tools
        tools = {}
        if hasattr(mcp, '_tools'):
            tools = mcp._tools
            print(f"🛠️  **REGISTERED TOOLS**: {len(tools)}")
            print("-" * 40)
            for i, (name, tool) in enumerate(tools.items(), 1):
                doc = getattr(tool.fn, '__doc__', 'No description')
                first_line = doc.split('\n')[0].strip() if doc else 'No description'
                print(f"{i:2d}. **{name}**")
                print(f"     {first_line}")
                
        # Get resources  
        resources = {}
        if hasattr(mcp, '_resources'):
            resources = mcp._resources
            print(f"\n📄 **REGISTERED RESOURCES**: {len(resources)}")
            print("-" * 40)
            for i, (name, resource) in enumerate(resources.items(), 1):
                print(f"{i:2d}. **{name}**")
                
        # Get prompts
        prompts = {}
        if hasattr(mcp, '_prompts'):
            prompts = mcp._prompts
            print(f"\n💬 **REGISTERED PROMPTS**: {len(prompts)}")
            print("-" * 40)
            for i, (name, prompt) in enumerate(prompts.items(), 1):
                doc = getattr(prompt.fn, '__doc__', 'No description')
                first_line = doc.split('\n')[0].strip() if doc else 'No description'
                print(f"{i:2d}. **{name}**")
                print(f"     {first_line}")
                
        # Summary
        print(f"\n📊 **SUMMARY**")
        print("=" * 60)
        print(f"✅ Total Tools: {len(tools)}")
        print(f"✅ Total Resources: {len(resources)}")  
        print(f"✅ Total Prompts: {len(prompts)}")
        print(f"✅ Server Type: Travel Concierge (FastMCP)")
        print(f"✅ Status: Fully loaded and ready")
        
        # Tool categories
        print(f"\n🏷️  **TOOL CATEGORIES**")
        print("-" * 40)
        
        flight_tools = [name for name in tools if 'flight' in name.lower()]
        hotel_tools = [name for name in tools if 'hotel' in name.lower()]
        activity_tools = [name for name in tools if any(x in name.lower() for x in ['event', 'activity'])]
        location_tools = [name for name in tools if any(x in name.lower() for x in ['geocode', 'distance', 'location'])]
        weather_tools = [name for name in tools if any(x in name.lower() for x in ['weather', 'condition', 'forecast'])]
        financial_tools = [name for name in tools if any(x in name.lower() for x in ['currency', 'stock', 'convert'])]
        
        categories = [
            ("✈️  Flight Search", flight_tools),
            ("🏨 Hotel Search", hotel_tools), 
            ("🎭 Events & Activities", activity_tools),
            ("🌍 Location Services", location_tools),
            ("🌦️  Weather Services", weather_tools),
            ("💰 Financial Services", financial_tools)
        ]
        
        for category, tool_list in categories:
            if tool_list:
                print(f"{category}: {len(tool_list)} tools")
                for tool in tool_list:
                    print(f"   • {tool}")
            else:
                print(f"{category}: 0 tools")
                
    except Exception as e:
        print(f"❌ Error analyzing server: {e}")
        
if __name__ == "__main__":
    analyze_server()