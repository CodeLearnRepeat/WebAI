#!/usr/bin/env python3
import json
import redis
import os
from datetime import datetime

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://:S0U8FJJglISDHBFVpc59mk3q9NKqsQjm@redis-13711.c124.us-central1-1.gce.redns.redis-cloud.com:13711")
TENANT_ID = "tenant_vVdw1P_8ur10FyG58wFClg"

def get_redis_client():
    """Create Redis client from URL"""
    return redis.from_url(REDIS_URL, decode_responses=True)

def check_tenant_config(tenant_id):
    """Check current tenant configuration"""
    r = get_redis_client()
    key = f"tenant:{tenant_id}"
    
    data = r.get(key)
    if not data:
        print(f"❌ No configuration found for tenant: {tenant_id}")
        return None
    
    config = json.loads(data)
    print(f"✅ Found tenant configuration for: {tenant_id}")
    print("\nCurrent configuration:")
    print("-" * 50)
    
    # Display config without sensitive data
    safe_config = config.copy()
    if 'openrouter_api_key' in safe_config:
        key_val = safe_config['openrouter_api_key']
        if key_val:
            safe_config['openrouter_api_key'] = f"{key_val[:10]}...{key_val[-4:]}" if len(key_val) > 14 else "***"
        else:
            safe_config['openrouter_api_key'] = "❌ MISSING"
    else:
        safe_config['openrouter_api_key'] = "❌ NOT SET"
    
    print(json.dumps(safe_config, indent=2))
    return config

def update_openrouter_key(tenant_id, new_api_key):
    """Update the OpenRouter API key for a tenant"""
    r = get_redis_client()
    key = f"tenant:{tenant_id}"
    
    # Get existing config
    data = r.get(key)
    if not data:
        print(f"❌ No configuration found for tenant: {tenant_id}")
        return False
    
    config = json.loads(data)
    
    # Update the API key
    old_key = config.get('openrouter_api_key', 'NOT SET')
    config['openrouter_api_key'] = new_api_key
    config['updated_at'] = datetime.utcnow().isoformat()
    
    # Save back to Redis
    r.set(key, json.dumps(config))
    
    print(f"\n✅ Successfully updated OpenRouter API key for tenant: {tenant_id}")
    print(f"   Old key: {old_key[:10] if old_key and len(old_key) > 10 else old_key}...")
    print(f"   New key: {new_api_key[:10]}...{new_api_key[-4:]}")
    
    return True

def main():
    print("=" * 60)
    print("WebAI Tenant OpenRouter API Key Fixer")
    print("=" * 60)
    
    # Step 1: Check current configuration
    print(f"\n1. Checking tenant: {TENANT_ID}")
    config = check_tenant_config(TENANT_ID)
    
    if not config:
        print("\n⚠️  Tenant not found in Redis!")
        print("Make sure the tenant was properly registered.")
        return
    
    # Step 2: Check if key needs updating
    current_key = config.get('openrouter_api_key', '')
    if not current_key:
        print("\n⚠️  OpenRouter API key is missing!")
    else:
        print(f"\n📌 Current OpenRouter API key: {current_key[:15]}...")
        
    # Step 3: Ask for new key
    print("\n2. Enter your OpenRouter API key")
    print("   (Get one from https://openrouter.ai/keys)")
    print("   Format: sk-or-v1-xxxxxxxxxxxxx")
    print("-" * 50)
    
    new_key = input("Enter OpenRouter API key (or press Enter to skip): ").strip()
    
    if not new_key:
        print("\n⏭️  Skipping update.")
        return
    
    if not new_key.startswith("sk-or-"):
        print("\n⚠️  Warning: Key doesn't start with 'sk-or-'. Are you sure this is correct?")
        confirm = input("Continue anyway? (y/N): ").strip().lower()
        if confirm != 'y':
            print("❌ Aborted.")
            return
    
    # Step 4: Update the key
    print("\n3. Updating configuration...")
    if update_openrouter_key(TENANT_ID, new_key):
        print("\n🎉 Success! The tenant configuration has been updated.")
        print("\n4. Verifying update...")
        check_tenant_config(TENANT_ID)
        print("\n✅ Your WebAI chat should now work with RAG enabled!")
    else:
        print("\n❌ Failed to update configuration.")

if __name__ == "__main__":
    main()
