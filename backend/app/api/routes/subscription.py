from fastapi import APIRouter, HTTPException, Header, Request, Depends
from fastapi.responses import JSONResponse
import json
import logging
from typing import Optional

from app.services.stripe_service import stripe_service
from app.schemas.subscription import (
    CustomerCreateRequest,
    CustomerResponse,
    CustomerByEmailRequest,
    CustomerByEmailResponse,
    SubscriptionCreateRequest,
    SubscriptionResponse,
    SubscriptionStatusResponse,
    SubscriptionCancelRequest,
    SubscriptionCancelResponse,
    WebhookResponse,
    SubscriptionError
)
from app.core.config import settings

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])
logger = logging.getLogger(__name__)

@router.post("/create-customer", response_model=CustomerResponse)
async def create_customer(request: CustomerCreateRequest):
    """Create a new Stripe customer"""
    try:
        result = await stripe_service.create_customer(
            email=request.email,
            name=request.name,
            metadata=request.metadata
        )
        return CustomerResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating customer: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/find-customer-by-email", response_model=CustomerByEmailResponse)
async def find_customer_by_email(request: CustomerByEmailRequest):
    """Find customer by email address"""
    try:
        customer_data = await stripe_service.get_customer_by_email(request.email)
        
        if customer_data:
            return CustomerByEmailResponse(
                found=True,
                customer_data=CustomerResponse(**customer_data)
            )
        else:
            return CustomerByEmailResponse(found=False)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error finding customer: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/create-subscription", response_model=SubscriptionResponse)
async def create_subscription(request: SubscriptionCreateRequest):
    """Create a $2/month subscription for a customer"""
    try:
        result = await stripe_service.create_subscription(
            customer_id=request.customer_id,
            tenant_id=request.tenant_id
        )
        return SubscriptionResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating subscription: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/status/{customer_id}", response_model=SubscriptionStatusResponse)
async def get_subscription_status(customer_id: str):
    """Get subscription status for a customer"""
    try:
        result = await stripe_service.get_subscription_status(customer_id)
        return SubscriptionStatusResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting subscription status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/cancel/{subscription_id}", response_model=SubscriptionCancelResponse)
async def cancel_subscription(
    subscription_id: str, 
    request: SubscriptionCancelRequest = SubscriptionCancelRequest()
):
    """Cancel a subscription"""
    try:
        result = await stripe_service.cancel_subscription(
            subscription_id=subscription_id,
            immediate=request.immediate
        )
        return SubscriptionCancelResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error cancelling subscription: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/webhooks/stripe", response_model=WebhookResponse)
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events"""
    try:
        # Get the raw body and signature
        payload = await request.body()
        signature = request.headers.get("stripe-signature")
        
        if not signature:
            logger.error("Missing Stripe signature header")
            raise HTTPException(status_code=400, detail="Missing stripe-signature header")
        
        # Verify webhook signature
        if not stripe_service.verify_webhook_signature(payload, signature):
            logger.error("Invalid webhook signature")
            raise HTTPException(status_code=400, detail="Invalid signature")
        
        # Parse the event
        try:
            event = json.loads(payload.decode('utf-8'))
        except json.JSONDecodeError:
            logger.error("Invalid JSON in webhook payload")
            raise HTTPException(status_code=400, detail="Invalid JSON")
        
        # Handle the event
        result = await stripe_service.handle_webhook_event(event)
        
        return WebhookResponse(
            status="handled",
            event=result.get("event", "unknown"),
            message="Webhook processed successfully",
            data=result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error handling webhook: {e}")
        return WebhookResponse(
            status="error",
            event="error",
            message=f"Error processing webhook: {str(e)}"
        )

# Additional utility endpoints

@router.get("/health")
async def subscription_health_check():
    """Health check for subscription service"""
    try:
        # Basic check to see if Stripe is configured
        if not settings.STRIPE_SECRET_KEY:
            return {
                "status": "warning",
                "message": "Stripe not configured",
                "stripe_configured": False
            }
        
        return {
            "status": "healthy",
            "message": "Subscription service is operational",
            "stripe_configured": True
        }
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            "status": "error",
            "message": f"Health check failed: {str(e)}",
            "stripe_configured": False
        }

@router.get("/config")
async def get_subscription_config():
    """Get subscription configuration (public info only)"""
    try:
        # Ensure price exists and get the price ID
        price_id = await stripe_service.ensure_price_exists()
        
        return {
            "monthly_price_amount": 200,  # $2.00 in cents
            "currency": "usd",
            "interval": "month",
            "stripe_publishable_key": settings.STRIPE_PUBLISHABLE_KEY,
            "price_id": price_id
        }
    except Exception as e:
        logger.error(f"Error getting subscription config: {e}")
        raise HTTPException(status_code=500, detail="Unable to get subscription configuration")

# Admin endpoints (require admin key)

@router.get("/admin/customer/{customer_id}/subscriptions")
async def admin_get_customer_subscriptions(
    customer_id: str,
    x_admin_key: str = Header(None)
):
    """Admin endpoint to get all subscriptions for a customer"""
    if x_admin_key != settings.WEBAI_ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Invalid admin key")
    
    try:
        result = await stripe_service.get_subscription_status(customer_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin error getting customer subscriptions: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/admin/subscription/{subscription_id}/reactivate")
async def admin_reactivate_subscription(
    subscription_id: str,
    x_admin_key: str = Header(None)
):
    """Admin endpoint to reactivate a cancelled subscription"""
    if x_admin_key != settings.WEBAI_ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Invalid admin key")
    
    try:
        # This would reactivate a subscription that was set to cancel at period end
        import stripe
        subscription = stripe.Subscription.modify(
            subscription_id,
            cancel_at_period_end=False
        )
        
        return {
            "subscription_id": subscription.id,
            "status": subscription.status,
            "cancel_at_period_end": subscription.cancel_at_period_end,
            "message": "Subscription reactivated successfully"
        }
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error reactivating subscription: {e}")
        raise HTTPException(status_code=400, detail=f"Stripe error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error reactivating subscription: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")