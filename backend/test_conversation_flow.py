#!/usr/bin/env python3
"""
Test conversation flow with the actual backend
"""

import asyncio
import aiohttp
import json
from datetime import datetime
import uuid

# Configuration - adjust as needed
API_URL = "http://localhost:8000"
TENANT_ID = "tenant_Tgyrz826g6McXjlQX173RA"  # Use an existing tenant ID
SESSION_ID = f"test_session_{uuid.uuid4().hex[:8]}"

async def send_chat_message(session: aiohttp.ClientSession, message: str, use_redis: bool = True):
    """Send a chat message and get the response"""
    url = f"{API_URL}/chat/stream"
    headers = {
        "X-Tenant-ID": TENANT_ID,
        "Content-Type": "application/json"
    }
    
    payload = {
        "message": message,
        "session_id": SESSION_ID,
        "use_redis_conversations": use_redis,
        "use_rag": False
    }
    
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Sending message:")
    print(f"  Session ID: {SESSION_ID}")
    print(f"  Use Redis: {use_redis}")
    print(f"  Message: '{message}'")
    
    try:
        async with session.post(url, json=payload, headers=headers) as response:
            if response.status != 200:
                text = await response.text()
                print(f"  ❌ Error {response.status}: {text}")
                return None
            
            # Read the streaming response
            full_response = ""
            async for line in response.content:
                line_str = line.decode('utf-8').strip()
                if line_str.startswith("data: "):
                    data = line_str[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                        full_response += content
                    except:
                        pass
            
            print(f"  ✅ Response: {full_response[:100]}{'...' if len(full_response) > 100 else ''}")
            return full_response
            
    except Exception as e:
        print(f"  ❌ Exception: {e}")
        return None

async def test_conversation_persistence():
    """Test if conversation context persists across messages"""
    print("=" * 80)
    print("TESTING CONVERSATION CONTEXT PERSISTENCE")
    print("=" * 80)
    print(f"Using Tenant ID: {TENANT_ID}")
    print(f"Using Session ID: {SESSION_ID}")
    
    async with aiohttp.ClientSession() as session:
        # Test 1: Send first message with context
        print("\n[TEST 1] Establishing context...")
        response1 = await send_chat_message(
            session, 
            "My name is Bob and I'm testing the chat system. I love programming in Python.",
            use_redis=True
        )
        
        if not response1:
            print("❌ Failed to get first response")
            return
        
        # Wait a moment
        await asyncio.sleep(2)
        
        # Test 2: Ask about the context
        print("\n[TEST 2] Testing context recall...")
        response2 = await send_chat_message(
            session,
            "What's my name and what programming language do I love?",
            use_redis=True
        )
        
        if not response2:
            print("❌ Failed to get second response")
            return
        
        # Analyze results
        print("\n" + "=" * 80)
        print("ANALYSIS:")
        print("=" * 80)
        
        response2_lower = response2.lower()
        
        name_found = "bob" in response2_lower
        language_found = "python" in response2_lower
        
        if name_found and language_found:
            print("✅ SUCCESS: Context fully maintained!")
            print("   - Name 'Bob' was remembered")
            print("   - Programming language 'Python' was remembered")
        elif name_found or language_found:
            print("⚠️  PARTIAL: Some context was maintained")
            print(f"   - Name 'Bob': {'✅ Found' if name_found else '❌ Not found'}")
            print(f"   - Language 'Python': {'✅ Found' if language_found else '❌ Not found'}")
        else:
            print("❌ FAILURE: No context was maintained")
            print("   The AI did not remember Bob or Python")
        
        print(f"\nFull response: {response2}")
        
        # Test 3: Test without Redis to confirm the difference
        print("\n[TEST 3] Testing WITHOUT Redis (should not have context)...")
        response3 = await send_chat_message(
            session,
            "What's my name?",
            use_redis=False  # Disable Redis
        )
        
        if response3:
            response3_lower = response3.lower()
            if "bob" not in response3_lower:
                print("✅ Confirmed: Without Redis, context is not maintained")
            else:
                print("❌ Unexpected: Context found even without Redis")

async def check_backend_health():
    """Check if the backend is running"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_URL}/health") as response:
                if response.status == 200:
                    print("✅ Backend is healthy")
                    return True
                else:
                    print(f"❌ Backend returned status {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Cannot connect to backend: {e}")
        return False

if __name__ == "__main__":
    print("Checking backend health...")
    if asyncio.run(check_backend_health()):
        asyncio.run(test_conversation_persistence())
    else:
        print("\n⚠️  Please ensure the backend is running on", API_URL)
        print("   Run: cd backend && uvicorn app.main:app --reload")