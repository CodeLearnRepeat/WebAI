#!/usr/bin/env python3
"""
Backend Payment System Diagnostic Script
Run this to diagnose backend payment configuration issues
"""

import os
import sys
import asyncio
import logging
from typing import Dict, Any

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.core.config import settings
from app.services.stripe_service import stripe_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_diagnostics():
    """Run comprehensive backend diagnostics"""
    
    print("🔍 WebAI Backend Payment Diagnostics")
    print("=====================================")
    
    # 1. Environment Variables Check
    print("\n📋 Environment Variables:")
    env_vars = {
        'STRIPE_SECRET_KEY': settings.STRIPE_SECRET_KEY,
        'STRIPE_PUBLISHABLE_KEY': settings.STRIPE_PUBLISHABLE_KEY,
        'STRIPE_WEBHOOK_SECRET': settings.STRIPE_WEBHOOK_SECRET,
        'WEBAI_ADMIN_KEY': settings.WEBAI_ADMIN_KEY,
    }
    
    for var, value in env_vars.items():
        if value and value != "":
            if 'KEY' in var:
                # Mask sensitive keys
                masked = f"{value[:8]}...{value[-4:]}" if len(value) > 12 else "***"
                print(f"  ✅ {var}: {masked}")
            else:
                print(f"  ✅ {var}: {value}")
        else:
            print(f"  ❌ {var}: Not set or empty")
    
    # 2. Stripe Service Initialization
    print("\n🔧 Stripe Service:")
    try:
        if not settings.STRIPE_SECRET_KEY:
            print("  ❌ Stripe not configured - STRIPE_SECRET_KEY missing")
            return
        
        # Test price creation/retrieval
        print("  🔄 Testing price creation...")
        price_id = await stripe_service.ensure_price_exists()
        print(f"  ✅ Price ID: {price_id}")
        
    except Exception as e:
        print(f"  ❌ Stripe service error: {e}")
        return
    
    # 3. Test API Endpoints
    print("\n🌐 API Endpoint Tests:")
    
    # Test health endpoint
    try:
        from app.api.routes.subscription import subscription_health_check
        health_result = await subscription_health_check()
        print(f"  ✅ Health endpoint: {health_result}")
    except Exception as e:
        print(f"  ❌ Health endpoint error: {e}")
    
    # Test config endpoint
    try:
        from app.api.routes.subscription import get_subscription_config
        config_result = await get_subscription_config()
        print(f"  ✅ Config endpoint: {config_result}")
    except Exception as e:
        print(f"  ❌ Config endpoint error: {e}")
    
    # 4. Test Stripe Operations
    print("\n💳 Stripe Operations Test:")
    
    try:
        # Test customer creation
        print("  🔄 Testing customer creation...")
        test_customer = await stripe_service.create_customer(
            email="test@example.com",
            name="Test User"
        )
        customer_id = test_customer['customer_id']
        print(f"  ✅ Test customer created: {customer_id}")
        
        # Test subscription status check
        print("  🔄 Testing subscription status...")
        status = await stripe_service.get_subscription_status(customer_id)
        print(f"  ✅ Subscription status: {status}")
        
        # Clean up test customer
        print("  🧹 Cleaning up test customer...")
        import stripe
        stripe.Customer.delete(customer_id)
        print("  ✅ Test customer deleted")
        
    except Exception as e:
        print(f"  ❌ Stripe operations error: {e}")
    
    print("\n🏁 Backend diagnostic complete!")

if __name__ == "__main__":
    asyncio.run(run_diagnostics())