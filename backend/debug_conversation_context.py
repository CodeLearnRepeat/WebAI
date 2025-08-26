#!/usr/bin/env python3
"""
Debug script to test conversation context persistence
"""

import asyncio
import json
import httpx
from datetime import datetime

# Configuration
API_URL = "http://localhost:8000"  # Update if needed
TENANT_ID = "test"  # Update with your test tenant ID
SESSION_ID = f"debug-session-{datetime.now().timestamp()}"

async def send_message(message: str, session_id: str):
    """Send a message and return the response"""
    url = f"{API_URL}/chat/stream"
    headers = {
        "X-Tenant-ID": TENANT_ID,
        "Content-Type": "application/json"
    }
    
    payload = {
        "message": message,
        "session_id": session_id,
        "use_redis_conversations": True,
        "use_rag": False
    }
    
    print(f"\n[{datetime.now().isoformat()}] Sending message:")
    print(f"  Session ID: {session_id}")
    print(f"  Message: {message}")
    print(f"  Payload: {json.dumps(payload, indent=2)}")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers)
        
        if response.status_code != 200:
            print(f"  ERROR: Status {response.status_code}")
            print(f"  Response: {response.text}")
            return None
            
        # Read streaming response
        full_response = ""
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                data = line[6:]
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                    content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    full_response += content
                except:
                    pass
        
        print(f"  Response: {full_response[:100]}...")
        return full_response

async def test_conversation_context():
    """Test if conversation context is maintained"""
    print("=" * 80)
    print("TESTING CONVERSATION CONTEXT PERSISTENCE")
    print("=" * 80)
    
    # Test 1: Send first message
    print("\n[TEST 1] Sending first message...")
    response1 = await send_message("My name is Alice and I like pizza.", SESSION_ID)
    
    if not response1:
        print("❌ Failed to get response for first message")
        return
    
    # Wait a bit
    await asyncio.sleep(2)
    
    # Test 2: Send second message asking about context
    print("\n[TEST 2] Testing context recall...")
    response2 = await send_message("What is my name and what do I like?", SESSION_ID)
    
    if not response2:
        print("❌ Failed to get response for second message")
        return
    
    # Check if context was maintained
    print("\n" + "=" * 80)
    print("RESULTS:")
    print("=" * 80)
    
    response2_lower = response2.lower()
    if "alice" in response2_lower and "pizza" in response2_lower:
        print("✅ SUCCESS: The AI remembered the context!")
        print(f"   Response contained both 'Alice' and 'pizza'")
    elif "alice" in response2_lower or "pizza" in response2_lower:
        print("⚠️  PARTIAL: The AI remembered some context")
        print(f"   Response: {response2}")
    else:
        print("❌ FAILURE: The AI did not remember the context")
        print(f"   Response: {response2}")
    
    # Test 3: Try with a different session ID to confirm isolation
    print("\n[TEST 3] Testing session isolation with different session ID...")
    different_session = f"different-{SESSION_ID}"
    response3 = await send_message("What is my name?", different_session)
    
    if response3:
        response3_lower = response3.lower()
        if "alice" not in response3_lower:
            print("✅ Session isolation works: Different session doesn't have context")
        else:
            print("❌ Session isolation issue: Different session has context from another session")

async def check_redis_connection():
    """Check if Redis is accessible"""
    print("\n[CHECKING REDIS CONNECTION]")
    try:
        from app.core.redis import get_conversation_redis
        r = get_conversation_redis()
        if r:
            # Try to ping Redis
            r.ping()
            print("✅ Redis is connected and accessible")
            
            # Check if any conversations exist
            keys = r.keys("conversation:*")
            print(f"   Found {len(keys)} existing conversation keys")
            if keys:
                print(f"   Sample keys: {keys[:3]}")
        else:
            print("❌ Redis client is None - check configuration")
    except Exception as e:
        print(f"❌ Redis connection error: {e}")

if __name__ == "__main__":
    # First check Redis
    asyncio.run(check_redis_connection())
    
    # Then test conversation context
    asyncio.run(test_conversation_context())