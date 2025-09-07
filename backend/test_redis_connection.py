#!/usr/bin/env python3
"""
Test Redis connection with the updated configuration
"""

import redis
import os
from datetime import datetime

# Load Redis URL from environment
REDIS_URL = ""

def test_redis():
    """Test Redis connection and basic operations"""
    print(f"[{datetime.now().isoformat()}] Testing Redis connection...")
    print(f"Redis URL: {REDIS_URL[:30]}...")
    
    try:
        # Connect to Redis
        r = redis.from_url(REDIS_URL)
        
        # Test ping
        r.ping()
        print("✅ Redis connection successful!")
        
        # Test set/get
        test_key = f"test:connection:{datetime.now().timestamp()}"
        test_value = "Hello Redis!"
        
        r.set(test_key, test_value)
        retrieved = r.get(test_key)
        
        if retrieved and retrieved.decode() == test_value:
            print("✅ Redis set/get operations work!")
        else:
            print("❌ Redis set/get failed")
        
        # Clean up test key
        r.delete(test_key)
        
        # Check existing conversation keys
        conversation_keys = r.keys("conversation:*")
        print(f"\n📊 Found {len(conversation_keys)} existing conversation keys")
        if conversation_keys:
            # Show a few examples
            for key in conversation_keys[:3]:
                key_str = key.decode() if isinstance(key, bytes) else key
                print(f"   - {key_str}")
                # Get the value to see if it contains messages
                value = r.get(key)
                if value:
                    import json
                    try:
                        data = json.loads(value)
                        print(f"     Contains {len(data)} messages")
                    except:
                        print(f"     Unable to parse value")
        
        return True
        
    except redis.ConnectionError as e:
        print(f"❌ Redis connection failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_redis()
    if not success:
        print("\n⚠️  Redis is not accessible. Check your configuration.")
    else:
        print("\n✅ Redis is properly configured and accessible!")