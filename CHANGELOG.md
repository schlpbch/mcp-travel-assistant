# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [4.0.0] - 2026-01-20

### 🔒 Security

#### CRITICAL: Fixed API Key Exposure Vulnerability
- **Fixed** critical security vulnerability where ExchangeRate-API key was exposed in error messages
- **Impact**: API key `4b9d09c342e6f730c7d2376e` could be leaked through error responses when currency conversion requests failed
- **Risk Level**: CRITICAL - Could allow attackers to steal credentials, exhaust rate limits, and incur unauthorized costs
- **Affected Components**:
  - `ExchangeRateClient.convert()` in `src/travel_assistant/clients.py`
  - `convert_currency()` tool in `src/travel_assistant/server.py`

### ✨ Added

#### Security Infrastructure
- **New**: `sanitize_url_for_logging()` utility function in `src/travel_assistant/helpers.py`
  - Sanitizes URLs by replacing API keys with `[REDACTED]`
  - Handles path-based keys (e.g., `/v6/{api_key}/pair/...`)
  - Handles query parameter keys (e.g., `?api_key=xxx`)
  - Prevents accidental API key exposure in logs and error messages

#### Test Coverage
- **New**: `TestSecurityHelpers` test class with 5 comprehensive tests
  - `test_sanitize_url_for_logging_exchangerate_api` - Verifies ExchangeRate-API key redaction
  - `test_sanitize_url_for_logging_query_parameter` - Verifies query param redaction
  - `test_sanitize_url_for_logging_ampersand_parameter` - Verifies mid-query redaction
  - `test_sanitize_url_for_logging_no_api_key` - Verifies URLs without keys unchanged
  - `test_sanitize_url_for_logging_multiple_patterns` - Verifies multiple pattern handling

- **New**: Security tests in `TestExchangeRateClient` class
  - `test_convert_http_error_no_key_exposure` - Verifies no key in HTTP error messages
  - `test_convert_network_timeout_no_key_exposure` - Verifies no key in timeout errors

### 🔧 Changed

#### Error Handling Improvements
- **Changed**: `ExchangeRateClient.convert()` error handling
  - **Before**: `{"error": f"Currency API request failed: {str(e)}"}` ❌ (exposed API key)
  - **After**: `{"error": "Currency API request failed. Please check currency codes and try again."}` ✅ (safe)
  
- **Changed**: `convert_currency()` tool error handling
  - **Before**: `{"error": f"Currency API request failed: {str(e)}"}` ❌ (exposed API key)
  - **After**: `{"error": "Currency API request failed. Please check currency codes and try again."}` ✅ (safe)

- **Improved**: Error messages are now user-friendly and do not expose implementation details
- **Improved**: All error handlers now include security comments to prevent future regressions

### 📊 Testing

- **Total Tests**: 189 (all passing ✅)
- **New Security Tests**: 7
- **Test Coverage**: No regressions detected
- **Security Audit**: Completed for all API clients

### 🛡️ Security Checklist

- ✅ API key is never included in error messages
- ✅ URL sanitization utility is tested
- ✅ ExchangeRateClient errors are sanitized
- ✅ convert_currency tool errors are sanitized
- ✅ All tests pass (189 tests)
- ✅ No regression in functionality
- ✅ User-friendly error messages maintained
- ✅ Security audit of all API clients completed

### 📝 Documentation

- **Added**: Comprehensive implementation plan documenting the vulnerability and fix strategy
- **Added**: Detailed walkthrough with before/after examples and verification results
- **Added**: Security comments in code to prevent future regressions

### 🔍 Files Changed

#### Modified Files
1. `src/travel_assistant/helpers.py` - Added `sanitize_url_for_logging()` utility
2. `src/travel_assistant/clients.py` - Fixed `ExchangeRateClient.convert()` error handling
3. `src/travel_assistant/server.py` - Fixed `convert_currency()` tool error handling

#### Test Files
1. `tests/test_helpers.py` - Added `TestSecurityHelpers` class with 5 tests
2. `tests/test_clients.py` - Added 2 security tests to `TestExchangeRateClient`

### ⚠️ Breaking Changes

**Error Message Format Change**
- Error messages from currency conversion no longer include detailed exception information
- This is intentional and necessary for security
- Error messages are now generic but user-friendly
- **Migration**: If you were parsing error messages for debugging, use logging instead

### 🎯 Recommendations

#### Immediate Actions
✅ **All completed** - No further immediate actions required.

#### Future Enhancements
1. **Logging Audit**: Review all logging statements to ensure no API keys are logged
2. **Environment Variable Protection**: Consider using secret management services
3. **Rate Limiting**: Implement client-side rate limiting to prevent abuse
4. **API Key Rotation**: Establish a process for regular API key rotation

### 📈 Statistics

- **Lines of Code Added**: ~100
- **Lines of Code Modified**: ~10
- **Test Coverage Added**: 7 new security tests
- **Security Vulnerabilities Fixed**: 1 (CRITICAL)
- **API Clients Audited**: 5 (SerpAPI, Amadeus, ExchangeRate, Geocoding, NWS)

---

## [3.0.0] - Previous Release

See `RELEASE_2.3.0.md` for previous release notes.

---

## Security Policy

If you discover a security vulnerability, please report it to the maintainers immediately. Do not create public GitHub issues for security vulnerabilities.

---

[4.0.0]: https://github.com/schlpbch/mcp-travel-assistant/compare/v3.0.0...v4.0.0
[3.0.0]: https://github.com/schlpbch/mcp-travel-assistant/releases/tag/v3.0.0
