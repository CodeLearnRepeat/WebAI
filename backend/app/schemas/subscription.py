from pydantic import BaseModel, validator, EmailStr
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime

# Customer schemas
class CustomerCreateRequest(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    metadata: Optional[Dict[str, str]] = None

class CustomerResponse(BaseModel):
    customer_id: str
    email: str
    name: Optional[str] = None
    created: int

# Subscription schemas
class SubscriptionCreateRequest(BaseModel):
    customer_id: str
    tenant_id: Optional[str] = None

class SubscriptionResponse(BaseModel):
    subscription_id: str
    customer_id: str
    status: str
    current_period_start: int
    current_period_end: int
    amount: int  # Amount in cents
    currency: str
    client_secret: Optional[str] = None

class SubscriptionDetails(BaseModel):
    subscription_id: str
    status: str
    current_period_start: int
    current_period_end: int
    cancel_at_period_end: bool
    created: int

class SubscriptionStatusResponse(BaseModel):
    customer_id: str
    has_subscription: bool
    status: str
    current_subscription_id: Optional[str] = None
    current_period_start: Optional[int] = None
    current_period_end: Optional[int] = None
    cancel_at_period_end: Optional[bool] = None
    subscriptions: List[SubscriptionDetails] = []

class SubscriptionCancelRequest(BaseModel):
    immediate: bool = False

class SubscriptionCancelResponse(BaseModel):
    subscription_id: str
    status: str
    cancel_at_period_end: bool
    current_period_end: Optional[int] = None
    cancelled_at: Optional[int] = None

# Webhook schemas
class WebhookEvent(BaseModel):
    event_type: str
    subscription_id: Optional[str] = None
    customer_id: Optional[str] = None
    subscription_status: Optional[str] = None
    invoice_id: Optional[str] = None
    amount_paid: Optional[int] = None

class WebhookResponse(BaseModel):
    status: Literal["handled", "unhandled", "error"]
    event: str
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

# Error schemas
class SubscriptionError(BaseModel):
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None

# Find customer by email
class CustomerByEmailRequest(BaseModel):
    email: EmailStr

class CustomerByEmailResponse(BaseModel):
    found: bool
    customer_data: Optional[CustomerResponse] = None