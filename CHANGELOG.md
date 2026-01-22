# Changelog

All notable changes to mcp-travel-assistant will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [4.2.0] - 2026-01-22

### Changed
- **Updated swiss-ai-mcp-commons to v1.1.0** with HTTP content negotiation support
- Enhanced JSON serialization capabilities with automatic compression
- Added framework integration helpers for FastAPI, Flask, and Starlette
- Improved bandwidth efficiency with smart gzip compression (60-80% reduction)

### Performance
- Content negotiation enables automatic response compression when beneficial
- Configurable compression thresholds (default: 1024 bytes)
- Backward compatible with existing API consumers

## [4.1.0] - 2026-01-22

### Added
- Production release with comprehensive travel planning services
- MCP tools for flight search, hotel booking, and destination discovery
- Integration with Amadeus API for real-time travel data
- Accessibility support with mcp-accessibility-models
- Geographic search and coordinate conversion
- Multi-modal travel planning support

### Features
- Flight search with real-time availability
- Hotel search and pricing
- Destination recommendations
- Point of interest discovery
- Weather integration
- Comprehensive travel itinerary planning

[4.2.0]: https://github.com/schlpbch/mcp-travel-assistant/compare/v4.1.0...v4.2.0
[4.1.0]: https://github.com/schlpbch/mcp-travel-assistant/releases/tag/v4.1.0
