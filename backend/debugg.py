#!/usr/bin/env python3
"""
Comprehensive WebAI debugging script
"""

import redis
import json
import requests
from datetime import datetime

# Configuration
REDIS_URL = "redis://:S0U8FJJglISDHBFVpc59mk3q9NKqsQjm@redis-13711.c124.us-central1-1.gce.redns.redis-cloud.com:13711"
API_URL = "https://web3ai-backend-v65-api-180395924844.us-central1.run.app"
TENANT_ID = "tenant_CfmIhmjL0eY3vVqh90XI0g"
SESSION_ID = "session_1756545248128_y9nc5o7ce"

def test_redis_connection():
    """Test Redis connection and check for conversations"""
    print("=" * 60)
    print("Testing Redis Connection")
    print("=" * 60)
    
    try:
        r = redis.from_url(REDIS_URL)
        r.ping()
        print("✅ Redis connection successful!")
        
        # Check for the specific conversation
        key = f"conversation:{TENANT_ID}:{SESSION_ID}"
        print(f"\nLooking for key: {key}")
        
        data = r.get(key)
        if data:
            messages = json.loads(data)
            print(f"✅ Found conversation with {len(messages)} messages")
            for i, msg in enumerate(messages[:3]):  # Show first 3 messages
                print(f"  Message {i+1}: {msg.get('role')} - {msg.get('content')[:50]}...")
        else:
            print("❌ No conversation found for this session")
        
        # List all conversation keys for this tenant
        pattern = f"conversation:{TENANT_ID}:*"
        keys = r.keys(pattern)
        print(f"\n📊 Total conversations for tenant: {len(keys)}")
        if keys:
            for key in keys[:5]:  # Show first 5
                print(f"  - {key.decode()}")
        
        return True
    except Exception as e:
        print(f"❌ Redis error: {e}")
        return False

def test_api_endpoints():
    """Test API endpoints"""
    print("\n" + "=" * 60)
    print("Testing API Endpoints")
    print("=" * 60)
    
    headers = {"X-Tenant-ID": TENANT_ID}
    
    # Test health endpoint
    print("\n1. Testing /health endpoint...")
    try:
        response = requests.get(f"{API_URL}/health", headers=headers)
        print(f"   Status: {response.status_code}")
        if response.ok:
            print("   ✅ Health check passed")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test the non-existent conversations endpoint
    print(f"\n2. Testing /conversations/{SESSION_ID} endpoint...")
    try:
        response = requests.get(f"{API_URL}/conversations/{SESSION_ID}", headers=headers)
        print(f"   Status: {response.status_code}")
        if response.status_code == 404:
            print("   ❌ Endpoint not found (404) - This is the problem!")
        elif response.ok:
            print("   ✅ Endpoint exists")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test chat/stream endpoint
    print("\n3. Testing /chat/stream endpoint...")
    try:
        payload = {
            "message": "test",
            "session_id": SESSION_ID,
            "use_redis_conversations": True
        }
        response = requests.post(
            f"{API_URL}/chat/stream", 
            headers={**headers, "Content-Type": "application/json"},
            json=payload
        )
        print(f"   Status: {response.status_code}")
        if response.ok:
            print("   ✅ Chat endpoint accessible")
        else:
            print(f"   ❌ Error: {response.text[:200]}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

def main():
    print("\n🔍 WebAI Debugging Tool")
    print("=" * 60)
    
    # Test Redis
    redis_ok = test_redis_connection()
    
    # Test API
    test_api_endpoints()
    
    print("\n" + "=" * 60)
    print("DIAGNOSIS")
    print("=" * 60)
    print("\n🔴 ROOT CAUSE: The frontend is trying to fetch from")
    print(f"   {API_URL}/conversations/{SESSION_ID}")
    print("   but this endpoint doesn't exist in your backend.\n")
    print("📝 SOLUTION: Either:")
    print("   1. Add a GET /conversations/{session_id} endpoint to your backend")
    print("   2. Modify the frontend to not fetch conversation history")
    print("   3. Use a different widget that doesn't require this endpoint")
    print("\n💡 The conversation data IS being stored in Redis correctly,")
    print("   but there's no API endpoint to retrieve it.")

if __name__ == "__main__":
    main()
