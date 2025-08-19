# API Key Generators

This document describes the API key generation system implemented for the WebAI project.

## Overview

Two types of API keys can be generated:

1. **Web Admin Keys**: UUID format for administrative access
2. **Tenant ID Keys**: Prefixed format for tenant identification

## Examples

### Web Admin Key
```
0f81c721-dffa-4d78-9c63-a4f4bb037f82
```
- Standard UUID v4 format
- Used for administrative authentication
- 36 characters (including hyphens)

### Tenant ID Key
```
tenant_PyKfd99yWzORf6ExHk0Nbw
```
- Starts with `tenant_` prefix
- Followed by URL-safe base64 encoded random data
- Total length: ~32-35 characters

## API Endpoints

All endpoints are available under `/api-keys` prefix.

## Curl Commands

Replace `YOUR_ADMIN_KEY` with your actual admin key and `http://localhost:8080` with your server URL.

### Generate Multiple Keys

**Generate 5 web_admin keys:**
```bash
curl -X POST "http://localhost:8080/api-keys/generate" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: YOUR_ADMIN_KEY" \
  -d '{
    "key_type": "web_admin",
    "count": 5
  }'
```

**Generate 3 tenant_id keys:**
```bash
curl -X POST "http://localhost:8080/api-keys/generate" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: YOUR_ADMIN_KEY" \
  -d '{
    "key_type": "tenant_id",
    "count": 3
  }'
```

### Generate Single Key (Quick)

**Generate one web_admin key:**
```bash
curl -X GET "http://localhost:8080/api-keys/generate/web_admin" \
  -H "X-Admin-Key: YOUR_ADMIN_KEY"
```

**Generate one tenant_id key:**
```bash
curl -X GET "http://localhost:8080/api-keys/generate/tenant_id" \
  -H "X-Admin-Key: YOUR_ADMIN_KEY"
```

### Analyze Key Information

**Analyze key via POST:**
```bash
curl -X POST "http://localhost:8080/api-keys/info" \
  -H "Content-Type: application/json" \
  -d '{
    "key": "tenant_XJahcRFsjkii-DLgFA-2Cw"
  }'
```

**Analyze web_admin key via GET:**
```bash
curl -X GET "http://localhost:8080/api-keys/info/8c63a9d4-32f6-4b95-a424-7e8c82857105"
```

**Analyze tenant_id key via GET:**
```bash
curl -X GET "http://localhost:8080/api-keys/info/tenant_XJahcRFsjkii-DLgFA-2Cw"
```

### Get Format Examples

**Get key format examples:**
```bash
curl -X GET "http://localhost:8080/api-keys/examples"
```

### Complete Example Workflow

**Step 1: Check available formats**
```bash
curl -X GET "http://localhost:8080/api-keys/examples"
```

**Step 2: Generate admin keys for your team**
```bash
curl -X POST "http://localhost:8080/api-keys/generate" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: YOUR_ADMIN_KEY" \
  -d '{
    "key_type": "web_admin",
    "count": 5
  }'
```

**Step 3: Generate tenant IDs for customers**
```bash
curl -X POST "http://localhost:8080/api-keys/generate" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: YOUR_ADMIN_KEY" \
  -d '{
    "key_type": "tenant_id",
    "count": 10
  }'
```

**Step 4: Verify a generated key**
```bash
curl -X GET "http://localhost:8080/api-keys/info/GENERATED_KEY_HERE"
```

### Error Handling Examples

**Invalid key type:**
```bash
curl -X GET "http://localhost:8080/api-keys/generate/invalid_type" \
  -H "X-Admin-Key: YOUR_ADMIN_KEY"
# Returns: 400 Bad Request
```

**Missing admin key:**
```bash
curl -X POST "http://localhost:8080/api-keys/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "key_type": "web_admin",
    "count": 1
  }'
# Returns: 401 Unauthorized
```

**Invalid admin key:**
```bash
curl -X POST "http://localhost:8080/api-keys/generate" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: wrong_key" \
  -d '{
    "key_type": "web_admin",
    "count": 1
  }'
# Returns: 401 Unauthorized
```

**Too many keys requested:**
```bash
curl -X POST "http://localhost:8080/api-keys/generate" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: YOUR_ADMIN_KEY" \
  -d '{
    "key_type": "web_admin",
    "count": 101
  }'
# Returns: 422 Validation Error
```

### Generate Multiple Keys

**POST** `/api-keys/generate`

Headers:
- `X-Admin-Key`: Required admin authentication

Request Body:
```json
{
    "key_type": "web_admin",  // or "tenant_id"
    "count": 5                // 1-100 keys
}
```

Response:
```json
{
    "keys": [
        {
            "key": "8c63a9d4-32f6-4b95-a424-7e8c82857105",
            "type": "web_admin",
            "generated_at": "2025-08-19T10:00:58.975452",
            "info": {
                "key": "8c63a9d4-32f6-4b95-a424-7e8c82857105",
                "generated_at": "2025-08-19T10:00:58.975452",
                "type": "web_admin",
                "format": "uuid"
            }
        }
    ],
    "total_generated": 1,
    "key_type": "web_admin"
}
```

### Generate Single Key (Quick)

**GET** `/api-keys/generate/{key_type}`

Parameters:
- `key_type`: Either `web_admin` or `tenant_id`

Headers:
- `X-Admin-Key`: Required admin authentication

Response:
```json
{
    "key": "tenant_XJahcRFsjkii-DLgFA-2Cw",
    "type": "tenant_id",
    "generated_at": "2025-08-19T10:00:58.975678",
    "info": {
        "key": "tenant_XJahcRFsjkii-DLgFA-2Cw",
        "generated_at": "2025-08-19T10:00:58.975678",
        "type": "tenant_id",
        "prefix": "tenant_",
        "identifier": "XJahcRFsjkii-DLgFA-2Cw"
    }
}
```

### Analyze Key Information

**POST** `/api-keys/info`

Request Body:
```json
{
    "key": "tenant_XJahcRFsjkii-DLgFA-2Cw"
}
```

**GET** `/api-keys/info/{key}`

Response:
```json
{
    "key": "tenant_XJahcRFsjkii-DLgFA-2Cw",
    "type": "tenant_id",
    "generated_at": "2025-08-19T10:00:58.975678",
    "prefix": "tenant_",
    "identifier": "XJahcRFsjkii-DLgFA-2Cw",
    "format": null,
    "valid": true
}
```

### Get Format Examples

**GET** `/api-keys/examples`

Response:
```json
{
    "web_admin": {
        "format": "UUID v4",
        "example": "0f81c721-dffa-4d78-9c63-a4f4bb037f82",
        "description": "Standard UUID format for web admin authentication"
    },
    "tenant_id": {
        "format": "tenant_ + base64url",
        "example": "tenant_PyKfd99yWzORf6ExHk0Nbw",
        "description": "Tenant identifier with 'tenant_' prefix and URL-safe base64 suffix"
    }
}
```

## Python Service Functions

### Direct Function Usage

```python
from app.services.api_keys import (
    generate_web_admin_key,
    generate_tenant_id,
    generate_api_key,
    generate_multiple_keys,
    get_key_info
)

# Generate specific key types
web_admin_key = generate_web_admin_key()
tenant_key = generate_tenant_id()

# Generic generation
key = generate_api_key("web_admin")  # or "tenant_id"

# Multiple keys
keys = generate_multiple_keys("tenant_id", count=5)

# Analyze key
info = get_key_info("tenant_XJahcRFsjkii-DLgFA-2Cw")
```

### Available Functions

- `generate_web_admin_key()` - Generate UUID format admin key
- `generate_tenant_id()` - Generate tenant_ prefixed key
- `generate_api_key(key_type)` - Generic generator
- `generate_multiple_keys(key_type, count)` - Batch generation
- `get_key_info(key)` - Analyze key format and type

## Integration with Existing System

The API key generators are integrated with the existing tenant system:

- The [`generate_tenant_id()`](backend/app/services/tenants.py:6) function in the tenant service now uses the centralized API key generator
- All tenant registration continues to work as before
- The new endpoints provide additional administrative capabilities

## Testing

Run the test suite to verify functionality:

```bash
cd backend && python3 test_api_key_generators.py
```

The test suite validates:
- UUID format for web_admin keys
- Prefix and base64url format for tenant_id keys
- Generic generator functionality
- Multiple key generation
- Key information analysis
- Uniqueness of generated keys

## Security Considerations

1. **Admin Authentication**: All generation endpoints require valid admin key
2. **Rate Limiting**: Consider implementing rate limiting for key generation
3. **Uniqueness**: All generators use cryptographically secure random sources
4. **Analysis Endpoint**: Key analysis endpoints don't require authentication as they only analyze format

## File Structure

```
backend/
├── app/
│   ├── services/
│   │   ├── api_keys.py          # Core generator functions
│   │   └── tenants.py           # Updated to use centralized generator
│   ├── schemas/
│   │   └── api_keys.py          # Pydantic models for API
│   ├── api/routes/
│   │   └── api_keys.py          # API endpoints
│   └── main.py                  # Updated to include API routes
├── test_api_key_generators.py   # Test suite
└── API_KEY_GENERATORS.md        # This documentation