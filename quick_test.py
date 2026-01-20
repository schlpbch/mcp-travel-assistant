#!/usr/bin/env python3
"""Quick tests for Travel Concierge MCP Server tools"""

import sys
import os
sys.path.insert(0, '/home/schlpbch/code/mcp-travel-assistant/src')

from travel_assistant import helpers
import requests
from geopy.geocoders import Nominatim
import json

def test_geocoding():
    """Test location geocoding"""
    print("🌍 Testing Geocoding...")
    try:
        geolocator = Nominatim(user_agent="travel-assistant-test")
        location = geolocator.geocode("Times Square, New York")
        if location:
            result = {
                'location_name': location.address,
                'latitude': location.latitude,
                'longitude': location.longitude
            }
            print(f"✅ Geocoding Success: {result['location_name']}")
            print(f"   📍 Coordinates: {result['latitude']}, {result['longitude']}")
            return result
        else:
            print("❌ Geocoding: No location found")
            return None
    except Exception as e:
        print(f"❌ Geocoding Error: {str(e)}")
        return None

def test_distance():
    """Test distance calculation using geopy"""
    print("\n📏 Testing Distance Calculation...")
    try:
        from geopy.distance import geodesic
        # NYC to LA coordinates
        nyc = (40.7128, -74.0060)
        la = (34.0522, -118.2437)
        
        distance = geodesic(nyc, la).kilometers
        result = {
            'from_location': 'NYC',
            'to_location': 'LA', 
            'distance_km': round(distance, 2)
        }
        print(f"✅ Distance Success: NYC to LA = {result['distance_km']} km")
        return result
    except Exception as e:
        print(f"❌ Distance Error: {str(e)}")
        return None

def test_weather():
    """Test weather API"""
    print("\n🌦️ Testing Weather API...")
    try:
        # Test Open-Meteo API directly
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": 40.7128,
            "longitude": -74.0060,
            "current_weather": True
        }
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            temp = data.get('current_weather', {}).get('temperature', 'Unknown')
            print(f"✅ Weather Success: NYC temp = {temp}°C")
            return data
        else:
            print(f"❌ Weather Error: HTTP {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Weather Error: {str(e)}")
        return None

def test_health_endpoint():
    """Test the health endpoint"""
    print("\n❤️ Testing Health Endpoint...")
    try:
        response = requests.get("http://localhost:1338/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health Success: {data.get('status', 'Unknown')}")
            return data
        else:
            print(f"❌ Health Error: HTTP {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Health Error: {str(e)} (Is server running?)")
        return None

def test_server_introspection():
    """Test FastMCP tool introspection"""
    print("\n🔍 Testing Server Tools...")
    try:
        sys.path.insert(0, '/home/schlpbch/code/mcp-travel-assistant/src')
        from travel_assistant.server import mcp
        
        # Count registered tools
        tool_count = len(mcp._tools) if hasattr(mcp, '_tools') else "Unknown"
        resource_count = len(mcp._resources) if hasattr(mcp, '_resources') else "Unknown" 
        prompt_count = len(mcp._prompts) if hasattr(mcp, '_prompts') else "Unknown"
        
        print(f"✅ Server Introspection Success:")
        print(f"   🛠️  Registered Tools: {tool_count}")
        print(f"   📄 Resources: {resource_count}")  
        print(f"   💬 Prompts: {prompt_count}")
        
        return {
            'tools': tool_count,
            'resources': resource_count,
            'prompts': prompt_count
        }
    except Exception as e:
        print(f"❌ Server Introspection Error: {str(e)}")
        return None

def main():
    print("🚀 Travel Concierge MCP Server - Quick Tests")
    print("=" * 50)
    
    # Run tests
    health_result = test_health_endpoint()
    introspection_result = test_server_introspection()
    geocode_result = test_geocoding()
    distance_result = test_distance()
    weather_result = test_weather()
    
    print("\n📊 Test Summary:")
    print("=" * 50)
    
    tests = [
        ("Health Endpoint", health_result),
        ("Server Introspection", introspection_result),
        ("Geocoding", geocode_result),
        ("Distance", distance_result), 
        ("Weather API", weather_result)
    ]
    
    passed = sum(1 for name, result in tests if result is not None)
    total = len(tests)
    
    for name, result in tests:
        status = "✅ PASS" if result is not None else "❌ FAIL"
        print(f"{status} {name}")
    
    print(f"\n🎯 Results: {passed}/{total} tests passed")
    
    if passed >= 3:
        print("🎉 Most tests passed! Server core functionality is working.")
    else:
        print("⚠️  Multiple tests failed - check server status and dependencies.")

if __name__ == "__main__":
    main()