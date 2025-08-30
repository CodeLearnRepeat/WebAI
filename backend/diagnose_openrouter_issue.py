#!/usr/bin/env python3
"""
Comprehensive diagnostic script to identify OpenRouter API key issues
"""
import json
import redis
import os
import httpx
import asyncio
from datetime import datetime

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://:S0U8FJJglISDHBFVpc59mk3q9NKqsQjm@redis-13711.c124.us-central1-1.gce.redns.redis-cloud.com:13711")
CONVERSATION_REDIS_URL = os.getenv("CONVERSATION_REDIS_URL", "redis://:S0U8FJJglISDHBFVpc59mk3q9NKqsQjm@redis-13711.c124.us-central1-1.gce.redns.redis-cloud.com:13711")
TENANT_ID = "tenant_vVdw1P_8ur10FyG58wFClg"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

def get_redis_client(url=None):
    """Create Redis client from URL"""
    redis_url = url or REDIS_URL
    print(f"Connecting to Redis: {redis_url[:30]}...")
    return redis.from_url(redis_url, decode_responses=True)

def check_tenant_in_redis():
    """Check tenant configuration in both Redis instances"""
    print("\n" + "="*60)
    print("1. CHECKING REDIS CONFIGURATIONS")
    print("="*60)
    
    configs = {}
    
    # Check main Redis
    print("\n📍 Main Redis (REDIS_URL):")
    try:
        r = get_redis_client(REDIS_URL)
        key = f"tenant:{TENANT_ID}"
        data = r.get(key)
        
        if data:
            config = json.loads(data)
            configs['main'] = config
            print(f"✅ Found tenant configuration")
            
            # Check for OpenRouter API key
            api_key = config.get('openrouter_api_key', '')
            if api_key:
                print(f"   OpenRouter API Key: {api_key[:15]}...{api_key[-4:] if len(api_key) > 19 else '***'}")
                print(f"   Key length: {len(api_key)} characters")
                print(f"   Starts with 'sk-or-': {api_key.startswith('sk-or-')}")
            else:
                print("   ❌ OpenRouter API Key: NOT SET")
            
            # Show other config
            print(f"   Model: {config.get('model', 'NOT SET')}")
            print(f"   RAG enabled: {config.get('rag', {}).get('enabled', False)}")
            print(f"   Active: {config.get('active', False)}")
            print(f"   Allowed domains: {config.get('allowed_domains', [])}")
        else:
            print(f"❌ No tenant configuration found for {TENANT_ID}")
    except Exception as e:
        print(f"❌ Error accessing main Redis: {e}")
    
    # Check conversation Redis if different
    if CONVERSATION_REDIS_URL and CONVERSATION_REDIS_URL != REDIS_URL:
        print("\n📍 Conversation Redis (CONVERSATION_REDIS_URL):")
        try:
            r = get_redis_client(CONVERSATION_REDIS_URL)
            key = f"tenant:{TENANT_ID}"
            data = r.get(key)
            
            if data:
                config = json.loads(data)
                configs['conversation'] = config
                print(f"✅ Found tenant configuration")
                api_key = config.get('openrouter_api_key', '')
                if api_key:
                    print(f"   OpenRouter API Key: {api_key[:15]}...{api_key[-4:] if len(api_key) > 19 else '***'}")
                else:
                    print("   ❌ OpenRouter API Key: NOT SET")
            else:
                print(f"❌ No tenant configuration found")
        except Exception as e:
            print(f"❌ Error accessing conversation Redis: {e}")
    else:
        print("\n📍 Conversation Redis: Same as main Redis")
    
    return configs

async def test_openrouter_api(api_key):
    """Test OpenRouter API directly"""
    print("\n" + "="*60)
    print("2. TESTING OPENROUTER API DIRECTLY")
    print("="*60)
    
    if not api_key:
        print("❌ No API key to test")
        return False
    
    print(f"\nTesting API key: {api_key[:15]}...{api_key[-4:]}")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": os.getenv("OPENROUTER_HTTP_REFERER", "https://webai-liart.vercel.app"),
        "X-Title": os.getenv("OPENROUTER_X_TITLE", "Web3AI Assistant"),
    }
    
    payload = {
        "model": "gpt-3.5-turbo",  # Using a cheap model for testing
        "messages": [
            {"role": "user", "content": "Say 'test successful' in 3 words"}
        ],
        "max_tokens": 10
    }
    
    print(f"Headers: {json.dumps({k: v if k != 'Authorization' else 'Bearer ***' for k, v in headers.items()}, indent=2)}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        async with httpx.AsyncClient() as client:
            print(f"\n🔄 Sending request to {OPENROUTER_API_URL}...")
            response = await client.post(
                OPENROUTER_API_URL,
                headers=headers,
                json=payload,
                timeout=30.0
            )
            
            print(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ API key is valid and working!")
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2)}")
                return True
            elif response.status_code == 401:
                print("❌ 401 Unauthorized - API key is invalid or not recognized")
                print(f"Response body: {response.text}")
                return False
            else:
                print(f"❌ Unexpected status code: {response.status_code}")
                print(f"Response body: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Error testing API: {e}")
        return False

def check_environment_variables():
    """Check environment variables"""
    print("\n" + "="*60)
    print("3. CHECKING ENVIRONMENT VARIABLES")
    print("="*60)
    
    env_vars = {
        "REDIS_URL": os.getenv("REDIS_URL"),
        "CONVERSATION_REDIS_URL": os.getenv("CONVERSATION_REDIS_URL"),
        "OPENROUTER_HTTP_REFERER": os.getenv("OPENROUTER_HTTP_REFERER"),
        "OPENROUTER_X_TITLE": os.getenv("OPENROUTER_X_TITLE"),
        "WEBAI_ADMIN_KEY": os.getenv("WEBAI_ADMIN_KEY"),
    }
    
    for key, value in env_vars.items():
        if value:
            if "KEY" in key or "redis" in key.lower():
                # Mask sensitive data
                display_value = f"{value[:20]}..." if len(value) > 20 else "***"
            else:
                display_value = value
            print(f"✅ {key}: {display_value}")
        else:
            print(f"❌ {key}: NOT SET")

def check_code_path():
    """Check the code path for API key usage"""
    print("\n" + "="*60)
    print("4. CODE PATH ANALYSIS")
    print("="*60)
    
    print("""
The error occurs in this flow:
1. chat.py:69 → Calls selfrag_run with api_key=tenant_config["openrouter_api_key"]
2. selfrag.py:30 → Calls chat_completion with the API key
3. openrouter.py:26 → Sets Authorization header as f"Bearer {api_key}"
4. openrouter.py:35 → Makes POST request to OpenRouter API

The 401 error means the API key in the Authorization header is rejected by OpenRouter.
""")

async def main():
    print("="*60)
    print("WEBAI OPENROUTER DIAGNOSTIC TOOL")
    print("="*60)
    print(f"Tenant ID: {TENANT_ID}")
    print(f"Timestamp: {datetime.utcnow().isoformat()}")
    
    # Step 1: Check Redis
    configs = check_tenant_in_redis()
    
    # Step 2: Check environment
    check_environment_variables()
    
    # Step 3: Test API key if found
    api_key = None
    if 'main' in configs:
        api_key = configs['main'].get('openrouter_api_key')
    
    if api_key:
        await test_openrouter_api(api_key)
    else:
        print("\n❌ Cannot test OpenRouter API - no API key found in Redis")
    
    # Step 4: Code path analysis
    check_code_path()
    
    # Summary
    print("\n" + "="*60)
    print("DIAGNOSIS SUMMARY")
    print("="*60)
    
    if not configs:
        print("❌ CRITICAL: No tenant configuration found in Redis")
        print("   Action: Register the tenant properly using the /register-tenant endpoint")
    elif not api_key:
        print("❌ CRITICAL: Tenant exists but OpenRouter API key is missing")
        print("   Action: Update the tenant configuration with a valid API key")
    else:
        print("🔍 Tenant configuration exists with an API key")
        print("   Check the test results above to see if the key is valid")
        print("\n   If the key test failed, possible issues:")
        print("   1. The API key is invalid or expired")
        print("   2. The API key doesn't have the right permissions")
        print("   3. OpenRouter account issues (billing, rate limits)")
        print("\n   If the key test succeeded but chat still fails:")
        print("   1. There might be a different Redis instance being used")
        print("   2. The application might be caching old configuration")
        print("   3. There might be an issue with the RAG-specific model or settings")

if __name__ == "__main__":
    asyncio.run(main())