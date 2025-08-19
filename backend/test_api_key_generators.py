#!/usr/bin/env python3
"""
Test script for API key generators to ensure correct formats.
"""

import uuid
import sys
import re
from app.services.api_keys import (
    generate_web_admin_key,
    generate_tenant_id,
    generate_api_key,
    generate_multiple_keys,
    get_key_info
)

def test_web_admin_key_format():
    """Test that web_admin keys are valid UUIDs."""
    print("Testing web_admin key format...")
    
    # Generate multiple keys to test consistency
    for i in range(5):
        key = generate_web_admin_key()
        print(f"  Generated web_admin key {i+1}: {key}")
        
        # Verify it's a valid UUID
        try:
            uuid_obj = uuid.UUID(key)
            assert str(uuid_obj) == key, f"UUID string mismatch: {uuid_obj} != {key}"
            print(f"    ✓ Valid UUID format")
        except ValueError as e:
            print(f"    ✗ Invalid UUID format: {e}")
            return False
    
    print("✓ web_admin key format test passed\n")
    return True

def test_tenant_id_format():
    """Test that tenant_id keys have correct prefix and format."""
    print("Testing tenant_id key format...")
    
    # Generate multiple keys to test consistency
    for i in range(5):
        key = generate_tenant_id()
        print(f"  Generated tenant_id {i+1}: {key}")
        
        # Verify it starts with "tenant_"
        if not key.startswith("tenant_"):
            print(f"    ✗ Does not start with 'tenant_': {key}")
            return False
        
        # Verify the suffix is URL-safe base64
        suffix = key[7:]  # Remove "tenant_" prefix
        if len(suffix) < 10:  # Should be reasonably long
            print(f"    ✗ Suffix too short: {suffix}")
            return False
        
        # Check for URL-safe base64 characters only
        if not re.match(r'^[A-Za-z0-9_-]+$', suffix):
            print(f"    ✗ Invalid characters in suffix: {suffix}")
            return False
        
        print(f"    ✓ Valid tenant_id format (prefix: tenant_, suffix: {suffix})")
    
    print("✓ tenant_id format test passed\n")
    return True

def test_generic_generator():
    """Test the generic generate_api_key function."""
    print("Testing generic API key generator...")
    
    # Test web_admin generation
    web_admin_key = generate_api_key("web_admin")
    print(f"  Generic web_admin key: {web_admin_key}")
    try:
        uuid.UUID(web_admin_key)
        print("    ✓ Valid UUID format")
    except ValueError:
        print("    ✗ Invalid UUID format")
        return False
    
    # Test tenant_id generation
    tenant_key = generate_api_key("tenant_id")
    print(f"  Generic tenant_id key: {tenant_key}")
    if not tenant_key.startswith("tenant_"):
        print("    ✗ Does not start with 'tenant_'")
        return False
    print("    ✓ Valid tenant_id format")
    
    # Test invalid key type
    try:
        generate_api_key("invalid_type")
        print("    ✗ Should have raised ValueError for invalid type")
        return False
    except ValueError:
        print("    ✓ Correctly raised ValueError for invalid type")
    
    print("✓ Generic generator test passed\n")
    return True

def test_multiple_keys_generation():
    """Test generating multiple keys at once."""
    print("Testing multiple keys generation...")
    
    # Test generating multiple web_admin keys
    web_admin_keys = generate_multiple_keys("web_admin", 3)
    print(f"  Generated {len(web_admin_keys)} web_admin keys:")
    for i, key in enumerate(web_admin_keys):
        print(f"    {i+1}: {key}")
        try:
            uuid.UUID(key)
        except ValueError:
            print(f"    ✗ Invalid UUID at index {i}")
            return False
    
    # Test generating multiple tenant_id keys
    tenant_keys = generate_multiple_keys("tenant_id", 3)
    print(f"  Generated {len(tenant_keys)} tenant_id keys:")
    for i, key in enumerate(tenant_keys):
        print(f"    {i+1}: {key}")
        if not key.startswith("tenant_"):
            print(f"    ✗ Invalid tenant_id at index {i}")
            return False
    
    # Test uniqueness
    all_keys = web_admin_keys + tenant_keys
    if len(set(all_keys)) != len(all_keys):
        print("    ✗ Generated duplicate keys")
        return False
    
    print("    ✓ All keys are unique")
    print("✓ Multiple keys generation test passed\n")
    return True

def test_key_info_analysis():
    """Test the key information analysis function."""
    print("Testing key info analysis...")
    
    # Test web_admin key analysis
    web_admin_key = generate_web_admin_key()
    info = get_key_info(web_admin_key)
    print(f"  Web admin key info: {info}")
    
    if info["type"] != "web_admin":
        print("    ✗ Incorrect type detection for web_admin key")
        return False
    
    # Test tenant_id key analysis
    tenant_key = generate_tenant_id()
    info = get_key_info(tenant_key)
    print(f"  Tenant key info: {info}")
    
    if info["type"] != "tenant_id":
        print("    ✗ Incorrect type detection for tenant_id key")
        return False
    
    if info.get("prefix") != "tenant_":
        print("    ✗ Incorrect prefix detection")
        return False
    
    # Test unknown key analysis
    unknown_key = "invalid_key_format"
    info = get_key_info(unknown_key)
    print(f"  Unknown key info: {info}")
    
    if info["type"] != "unknown":
        print("    ✗ Should detect unknown key type")
        return False
    
    print("✓ Key info analysis test passed\n")
    return True

def main():
    """Run all tests."""
    print("=== API Key Generator Tests ===\n")
    
    tests = [
        test_web_admin_key_format,
        test_tenant_id_format,
        test_generic_generator,
        test_multiple_keys_generation,
        test_key_info_analysis
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ Test {test_func.__name__} failed with exception: {e}\n")
            failed += 1
    
    print("=== Test Results ===")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total:  {passed + failed}")
    
    if failed == 0:
        print("\n🎉 All tests passed! API key generators are working correctly.")
        return 0
    else:
        print(f"\n❌ {failed} test(s) failed. Please check the implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())