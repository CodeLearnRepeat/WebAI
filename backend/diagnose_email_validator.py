#!/usr/bin/env python3
"""
Diagnostic script to confirm email-validator dependency issue
"""
import sys

def test_email_validator_import():
    """Test if email-validator can be imported directly"""
    try:
        import email_validator
        print("✅ email_validator module found")
        print(f"   Version: {email_validator.__version__}")
        return True
    except ImportError as e:
        print("❌ email_validator module NOT found")
        print(f"   Error: {e}")
        return False

def test_pydantic_email_import():
    """Test if pydantic EmailStr can be imported (which requires email-validator)"""
    try:
        from pydantic import EmailStr
        print("✅ pydantic.EmailStr import successful")
        return True
    except ImportError as e:
        print("❌ pydantic.EmailStr import FAILED")
        print(f"   Error: {e}")
        return False

def test_pydantic_email_validation():
    """Test actual email validation functionality"""
    try:
        from pydantic import BaseModel, EmailStr
        
        class TestModel(BaseModel):
            email: EmailStr
        
        # Test valid email
        test_obj = TestModel(email="test@example.com")
        print("✅ EmailStr validation working")
        print(f"   Validated email: {test_obj.email}")
        return True
    except Exception as e:
        print("❌ EmailStr validation FAILED")
        print(f"   Error: {e}")
        return False

def main():
    print("🔍 Diagnosing email-validator dependency issue...")
    print("=" * 50)
    
    results = []
    results.append(test_email_validator_import())
    results.append(test_pydantic_email_import()) 
    results.append(test_pydantic_email_validation())
    
    print("\n📋 Summary:")
    print("=" * 50)
    
    if all(results):
        print("✅ All tests passed - email validation working correctly")
        sys.exit(0)
    else:
        print("❌ Email validation dependency issue confirmed")
        print("\n💡 Solution: Add 'email-validator' to requirements.txt")
        print("   or use 'pydantic[email]' to include email validation extras")
        sys.exit(1)

if __name__ == "__main__":
    main()