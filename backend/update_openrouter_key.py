"""
Update OpenRouter API key for tenant
"""
import json
import redis
import os
import httpx
import asyncio
from datetime import datetime

# Configuration
REDIS_URL = "redis://:S0U8FJJglISDHBFVpc59mk3q9NKqsQjm@redis-13711.c124.us-central1-1.gce.redns.redis-cloud.com:13711"
TENANT_ID = "tenant_vVdw1P_8ur10FyG58wFClg"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

def get_redis_client():
    """Create Redis client from URL"""
    return redis.from_url(REDIS_URL, decode_responses=True)

async def validate_api_key(api_key):
    """Validate an OpenRouter API key"""
    print(f"\n🔍 Validating API key: {api_key[:15]}...{api_key[-4:]}")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://webai-liart.vercel.app",
        "X-Title": "Web3AI Assistant",
    }
    
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": "test"}],
        "max_tokens": 1
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                OPENROUTER_API_URL,
                headers=headers,
                json=payload,
                timeout=30.0
            )
            
            if response.status_code == 200:
                print("✅ API key is VALID!")
                return True
            elif response.status_code == 401:
                print(f"❌ API key is INVALID: {response.text}")
                return False
            else:
                print(f"⚠️  Unexpected response ({response.status_code}): {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Error validating API key: {e}")
        return False

def update_tenant_config(new_api_key):
    """Update the tenant configuration with new API key"""
    r = get_redis_client()
    key = f"tenant:{TENANT_ID}"
    
    # Get existing config
    data = r.get(key)
    if not data:
        print(f"❌ No configuration found for tenant: {TENANT_ID}")
        return False
    
    config = json.loads(data)
    old_key = config.get('openrouter_api_key', 'NOT SET')
    
    # Update the API key
    config['openrouter_api_key'] = new_api_key
    config['updated_at'] = datetime.utcnow().isoformat()
    
    # Save back to Redis
    r.set(key, json.dumps(config))
    
    print(f"\n✅ Successfully updated configuration in Redis")
    print(f"   Old key: {old_key[:15] if old_key and len(old_key) > 15 else old_key}...")
    print(f"   New key: {new_api_key[:15]}...{new_api_key[-4:]}")
    
    return True

async def main():
    print("="*60)
    print("OPENROUTER API KEY UPDATER")
    print("="*60)
    print(f"Tenant: {TENANT_ID}")
    
    # Check current configuration
    r = get_redis_client()
    key = f"tenant:{TENANT_ID}"
    data = r.get(key)
    
    if not data:
        print(f"\n❌ No tenant configuration found!")
        print("Please register the tenant first.")
        return
    
    config = json.loads(data)
    current_key = config.get('openrouter_api_key', '')
    
    print(f"\n📍 Current configuration:")
    print(f"   Model: {config.get('model', 'NOT SET')}")
    print(f"   RAG enabled: {config.get('rag', {}).get('enabled', False)}")
    
    if current_key:
        print(f"   Current API key: {current_key[:15]}...{current_key[-4:]}")
        
        # Test current key
        print("\n🔄 Testing current API key...")
        is_valid = await validate_api_key(current_key)
        
        if is_valid:
            print("\n✨ Current API key is already valid!")
            confirm = input("\nDo you still want to update it? (y/N): ").strip().lower()
            if confirm != 'y':
                print("✅ Keeping current valid API key.")
                return
    else:
        print("   Current API key: NOT SET")
    
    # Get new API key
    print("\n" + "="*60)
    print("📝 Enter your new OpenRouter API key")
    print("   Get one from: https://openrouter.ai/keys")
    print("   Format: sk-or-v1-xxxxxxxxxxxxx")
    print("="*60)
    
    new_key = input("\nEnter API key: ").strip()
    
    if not new_key:
        print("❌ No key provided. Exiting.")
        return
    
    # Validate format
    if not new_key.startswith("sk-or-"):
        print(f"\n⚠️  Warning: Key doesn't start with 'sk-or-'")
        print(f"   Your key starts with: {new_key[:10]}")
        confirm = input("Continue anyway? (y/N): ").strip().lower()
        if confirm != 'y':
            print("❌ Aborted.")
            return
    
    # Validate the new key
    is_valid = await validate_api_key(new_key)
    
    if not is_valid:
        print("\n❌ The API key is INVALID!")
        print("Please check:")
        print("1. You copied the complete key")
        print("2. The key hasn't expired")
        print("3. Your OpenRouter account is active")
        
        confirm = input("\nUpdate anyway? (y/N): ").strip().lower()
        if confirm != 'y':
            print("❌ Aborted.")
            return
    
    # Update the configuration
    print("\n🔄 Updating configuration...")
    if update_tenant_config(new_key):
        print("\n🎉 SUCCESS! Configuration updated.")
        
        if is_valid:
            print("✅ Your WebAI chat should now work properly!")
        else:
            print("⚠️  Warning: The API key appears invalid. You may still get 401 errors.")
    else:
        print("\n❌ Failed to update configuration.")

if __name__ == "__main__":
    asyncio.run(main())