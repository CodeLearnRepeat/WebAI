import stripe
import logging
from typing import Dict, Optional, Any
from fastapi import HTTPException
from app.core.config import settings

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY
stripe.api_version = "2023-10-16"

logger = logging.getLogger(__name__)

class StripeService:
    def __init__(self):
        if not settings.STRIPE_SECRET_KEY:
            logger.warning("STRIPE_SECRET_KEY not configured")
        
        # $2/month subscription price ID - this will be created if it doesn't exist
        self.monthly_price_id = None
        
    async def ensure_price_exists(self) -> str:
        """Ensure the $2/month price exists in Stripe, create if needed"""
        try:
            # First try to find existing price
            prices = stripe.Price.list(
                product_data={"name": "WebAI Subscription"},
                currency="usd",
                recurring={"interval": "month"},
                unit_amount=200,  # $2.00 in cents
                limit=1
            )
            
            if prices.data:
                self.monthly_price_id = prices.data[0].id
                logger.info(f"Found existing price: {self.monthly_price_id}")
                return self.monthly_price_id
            
            # Create product and price if not found
            product = stripe.Product.create(
                name="WebAI Subscription",
                description="Monthly subscription to WebAI platform",
                type="service"
            )
            
            price = stripe.Price.create(
                product=product.id,
                unit_amount=200,  # $2.00 in cents
                currency="usd",
                recurring={"interval": "month"},
                nickname="WebAI Monthly"
            )
            
            self.monthly_price_id = price.id
            logger.info(f"Created new price: {self.monthly_price_id}")
            return self.monthly_price_id
            
        except stripe.error.StripeError as e:
            logger.error(f"Error ensuring price exists: {e}")
            raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")

    async def create_customer(self, email: str, name: Optional[str] = None, metadata: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Create a new Stripe customer"""
        try:
            customer_data = {
                "email": email,
                "metadata": metadata or {}
            }
            
            if name:
                customer_data["name"] = name
                
            customer = stripe.Customer.create(**customer_data)
            
            logger.info(f"Created customer: {customer.id}")
            return {
                "customer_id": customer.id,
                "email": customer.email,
                "name": customer.name,
                "created": customer.created
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Error creating customer: {e}")
            raise HTTPException(status_code=400, detail=f"Stripe error: {str(e)}")

    async def create_subscription(self, customer_id: str, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a $2/month subscription for a customer"""
        try:
            # Ensure price exists
            price_id = await self.ensure_price_exists()
            
            metadata = {}
            if tenant_id:
                metadata["tenant_id"] = tenant_id
            
            subscription = stripe.Subscription.create(
                customer=customer_id,
                items=[{"price": price_id}],
                payment_behavior="default_incomplete",
                payment_settings={"save_default_payment_method": "on_subscription"},
                expand=["latest_invoice.payment_intent"],
                metadata=metadata
            )
            
            logger.info(f"Created subscription: {subscription.id}")
            
            return {
                "subscription_id": subscription.id,
                "customer_id": customer_id,
                "status": subscription.status,
                "current_period_start": subscription.current_period_start,
                "current_period_end": subscription.current_period_end,
                "amount": 200,  # $2.00 in cents
                "currency": "usd",
                "client_secret": subscription.latest_invoice.payment_intent.client_secret if subscription.latest_invoice.payment_intent else None
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Error creating subscription: {e}")
            raise HTTPException(status_code=400, detail=f"Stripe error: {str(e)}")

    async def get_subscription_status(self, customer_id: str) -> Dict[str, Any]:
        """Get subscription status for a customer"""
        try:
            # Get customer's subscriptions
            subscriptions = stripe.Subscription.list(
                customer=customer_id,
                status="all",
                limit=10
            )
            
            if not subscriptions.data:
                return {
                    "customer_id": customer_id,
                    "has_subscription": False,
                    "status": "none",
                    "subscriptions": []
                }
            
            # Get the most recent subscription
            latest_subscription = subscriptions.data[0]
            
            subscription_data = []
            for sub in subscriptions.data:
                subscription_data.append({
                    "subscription_id": sub.id,
                    "status": sub.status,
                    "current_period_start": sub.current_period_start,
                    "current_period_end": sub.current_period_end,
                    "cancel_at_period_end": sub.cancel_at_period_end,
                    "created": sub.created
                })
            
            return {
                "customer_id": customer_id,
                "has_subscription": True,
                "status": latest_subscription.status,
                "current_subscription_id": latest_subscription.id,
                "current_period_start": latest_subscription.current_period_start,
                "current_period_end": latest_subscription.current_period_end,
                "cancel_at_period_end": latest_subscription.cancel_at_period_end,
                "subscriptions": subscription_data
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Error getting subscription status: {e}")
            raise HTTPException(status_code=400, detail=f"Stripe error: {str(e)}")

    async def cancel_subscription(self, subscription_id: str, immediate: bool = False) -> Dict[str, Any]:
        """Cancel a subscription"""
        try:
            if immediate:
                # Cancel immediately
                subscription = stripe.Subscription.cancel(subscription_id)
            else:
                # Cancel at period end
                subscription = stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True
                )
            
            logger.info(f"Cancelled subscription: {subscription_id}")
            
            return {
                "subscription_id": subscription.id,
                "status": subscription.status,
                "cancel_at_period_end": subscription.cancel_at_period_end,
                "current_period_end": subscription.current_period_end,
                "cancelled_at": subscription.canceled_at
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Error cancelling subscription: {e}")
            raise HTTPException(status_code=400, detail=f"Stripe error: {str(e)}")

    async def get_customer_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Find customer by email address"""
        try:
            customers = stripe.Customer.list(email=email, limit=1)
            
            if customers.data:
                customer = customers.data[0]
                return {
                    "customer_id": customer.id,
                    "email": customer.email,
                    "name": customer.name,
                    "created": customer.created
                }
            
            return None
            
        except stripe.error.StripeError as e:
            logger.error(f"Error finding customer by email: {e}")
            raise HTTPException(status_code=400, detail=f"Stripe error: {str(e)}")

    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """Verify Stripe webhook signature"""
        try:
            stripe.Webhook.construct_event(
                payload, signature, settings.STRIPE_WEBHOOK_SECRET
            )
            return True
        except ValueError:
            logger.error("Invalid payload in webhook")
            return False
        except stripe.error.SignatureVerificationError:
            logger.error("Invalid signature in webhook")
            return False

    async def handle_webhook_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Stripe webhook events"""
        event_type = event.get("type")
        event_data = event.get("data", {}).get("object", {})
        
        logger.info(f"Handling webhook event: {event_type}")
        
        if event_type == "customer.subscription.created":
            return await self._handle_subscription_created(event_data)
        elif event_type == "customer.subscription.updated":
            return await self._handle_subscription_updated(event_data)
        elif event_type == "customer.subscription.deleted":
            return await self._handle_subscription_deleted(event_data)
        elif event_type == "invoice.payment_succeeded":
            return await self._handle_payment_succeeded(event_data)
        elif event_type == "invoice.payment_failed":
            return await self._handle_payment_failed(event_data)
        else:
            logger.info(f"Unhandled webhook event type: {event_type}")
            return {"status": "unhandled", "event_type": event_type}

    async def _handle_subscription_created(self, subscription_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle subscription creation webhook"""
        subscription_id = subscription_data.get("id")
        customer_id = subscription_data.get("customer")
        status = subscription_data.get("status")
        
        logger.info(f"Subscription created: {subscription_id} for customer {customer_id}")
        
        # Here you could update your database, send notifications, etc.
        return {
            "status": "handled",
            "event": "subscription_created",
            "subscription_id": subscription_id,
            "customer_id": customer_id,
            "subscription_status": status
        }

    async def _handle_subscription_updated(self, subscription_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle subscription update webhook"""
        subscription_id = subscription_data.get("id")
        customer_id = subscription_data.get("customer")
        status = subscription_data.get("status")
        
        logger.info(f"Subscription updated: {subscription_id} status: {status}")
        
        return {
            "status": "handled",
            "event": "subscription_updated",
            "subscription_id": subscription_id,
            "customer_id": customer_id,
            "subscription_status": status
        }

    async def _handle_subscription_deleted(self, subscription_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle subscription deletion webhook"""
        subscription_id = subscription_data.get("id")
        customer_id = subscription_data.get("customer")
        
        logger.info(f"Subscription deleted: {subscription_id}")
        
        return {
            "status": "handled",
            "event": "subscription_deleted",
            "subscription_id": subscription_id,
            "customer_id": customer_id
        }

    async def _handle_payment_succeeded(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle successful payment webhook"""
        invoice_id = invoice_data.get("id")
        customer_id = invoice_data.get("customer")
        subscription_id = invoice_data.get("subscription")
        amount_paid = invoice_data.get("amount_paid")
        
        logger.info(f"Payment succeeded: {invoice_id} amount: {amount_paid}")
        
        return {
            "status": "handled",
            "event": "payment_succeeded",
            "invoice_id": invoice_id,
            "customer_id": customer_id,
            "subscription_id": subscription_id,
            "amount_paid": amount_paid
        }

    async def _handle_payment_failed(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle failed payment webhook"""
        invoice_id = invoice_data.get("id")
        customer_id = invoice_data.get("customer")
        subscription_id = invoice_data.get("subscription")
        
        logger.warning(f"Payment failed: {invoice_id}")
        
        return {
            "status": "handled",
            "event": "payment_failed",
            "invoice_id": invoice_id,
            "customer_id": customer_id,
            "subscription_id": subscription_id
        }

# Global instance
stripe_service = StripeService()