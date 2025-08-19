# API Key Generators - Curl Commands Quick Reference

Replace `YOUR_ADMIN_KEY` with your actual admin key and `http://localhost:8080` with your server URL.

## 🔑 Generate Keys

### Multiple Keys
```bash
# Generate 5 web_admin keys
curl -X POST "http://localhost:8080/api-keys/generate" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: YOUR_ADMIN_KEY" \
  -d '{"key_type": "web_admin", "count": 5}'

# Generate 3 tenant_id keys  
curl -X POST "http://localhost:8080/api-keys/generate" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: YOUR_ADMIN_KEY" \
  -d '{"key_type": "tenant_id", "count": 3}'
```

### Single Keys (Quick)
```bash
# Generate one web_admin key
curl -X GET "http://localhost:8080/api-keys/generate/web_admin" \
  -H "X-Admin-Key: YOUR_ADMIN_KEY"

# Generate one tenant_id key
curl -X GET "http://localhost:8080/api-keys/generate/tenant_id" \
  -H "X-Admin-Key: YOUR_ADMIN_KEY"
```

## 🔍 Analyze Keys

```bash
# Analyze via POST
curl -X POST "http://localhost:8080/api-keys/info" \
  -H "Content-Type: application/json" \
  -d '{"key": "tenant_XJahcRFsjkii-DLgFA-2Cw"}'

# Analyze via GET
curl -X GET "http://localhost:8080/api-keys/info/tenant_XJahcRFsjkii-DLgFA-2Cw"
```

## 📖 Get Examples

```bash
# Get key format examples
curl -X GET "http://localhost:8080/api-keys/examples"
```

## 🚀 Quick Start

```bash
# 1. Check formats
curl -X GET "http://localhost:8080/api-keys/examples"

# 2. Generate admin key
curl -X GET "http://localhost:8080/api-keys/generate/web_admin" \
  -H "X-Admin-Key: YOUR_ADMIN_KEY"

# 3. Generate tenant key  
curl -X GET "http://localhost:8080/api-keys/generate/tenant_id" \
  -H "X-Admin-Key: YOUR_ADMIN_KEY"
```

## Expected Responses

### Web Admin Key
```json
{
  "key": "8c63a9d4-32f6-4b95-a424-7e8c82857105",
  "type": "web_admin",
  "generated_at": "2025-08-19T10:00:58.975452"
}
```

### Tenant ID Key
```json
{
  "key": "tenant_XJahcRFsjkii-DLgFA-2Cw", 
  "type": "tenant_id",
  "generated_at": "2025-08-19T10:00:58.975678"
}