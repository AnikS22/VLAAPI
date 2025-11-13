"""Billing and subscription management endpoints with Stripe integration."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from stripe.error import StripeError

from src.api.routers.auth import get_current_user
from src.core.config import get_settings
from src.core.database import get_db_session
from src.models.database import Customer, User
from src.services.billing.stripe_service import StripeService

router = APIRouter(prefix="/v1/billing", tags=["Billing"])
settings = get_settings()
logger = logging.getLogger(__name__)


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================


class CreateCheckoutRequest(BaseModel):
    """Create Stripe checkout session request."""

    tier: str = Field(..., description="Tier to subscribe to (pro or enterprise)")
    success_url: str = Field(..., description="URL to redirect after successful payment")
    cancel_url: str = Field(..., description="URL to redirect if payment is cancelled")


class CheckoutSessionResponse(BaseModel):
    """Checkout session response."""

    session_id: str
    checkout_url: str


class BillingPortalResponse(BaseModel):
    """Billing portal response."""

    portal_url: str


class SubscriptionResponse(BaseModel):
    """Subscription information."""

    subscription_id: str | None
    status: str | None
    tier: str
    monthly_quota: int | None
    monthly_usage: int
    cancel_at_period_end: bool | None


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


async def get_customer_for_user(user: User, db: AsyncSession) -> Customer:
    """Get customer for authenticated user."""
    result = await db.execute(
        select(Customer).where(Customer.user_id == user.user_id)
    )
    customer = result.scalar_one_or_none()

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer profile not found"
        )

    return customer


def get_price_id_for_tier(tier: str) -> str:
    """Get Stripe price ID for tier.

    Args:
        tier: Tier name (pro or enterprise)

    Returns:
        Stripe price ID

    Raises:
        HTTPException: If tier is invalid or price ID not configured
    """
    if tier == "pro":
        price_id = settings.stripe_price_id_pro
        if not price_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Pro tier price ID not configured"
            )
        return price_id
    elif tier == "enterprise":
        price_id = settings.stripe_price_id_enterprise
        if not price_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Enterprise tier price ID not configured"
            )
        return price_id
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid tier. Must be 'pro' or 'enterprise'"
        )


# ============================================================================
# ENDPOINTS
# ============================================================================


@router.post("/checkout", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    request: CreateCheckoutRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> CheckoutSessionResponse:
    """Create a Stripe checkout session for subscription upgrade.

    Args:
        request: Checkout request with tier and URLs
        current_user: Current authenticated user
        db: Database session

    Returns:
        CheckoutSessionResponse with session ID and checkout URL

    Raises:
        HTTPException: If Stripe is not enabled or checkout creation fails
    """
    if not settings.enable_stripe:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe billing is not enabled"
        )

    customer = await get_customer_for_user(current_user, db)

    # Create Stripe customer if not exists
    if not customer.stripe_customer_id:
        try:
            stripe_customer_id = await StripeService.create_customer(
                email=customer.email,
                name=current_user.full_name,
                metadata={
                    "customer_id": str(customer.customer_id),
                    "user_id": str(current_user.user_id),
                },
            )
            customer.stripe_customer_id = stripe_customer_id
            await db.commit()
        except StripeError as e:
            logger.error(f"Failed to create Stripe customer: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create billing account"
            )

    # Get price ID for requested tier
    price_id = get_price_id_for_tier(request.tier)

    # Create checkout session
    try:
        session_data = await StripeService.create_checkout_session(
            customer_id=customer.stripe_customer_id,
            price_id=price_id,
            success_url=request.success_url,
            cancel_url=request.cancel_url,
            metadata={
                "customer_id": str(customer.customer_id),
                "tier": request.tier,
            },
        )

        return CheckoutSessionResponse(
            session_id=session_data["session_id"],
            checkout_url=session_data["url"],
        )
    except StripeError as e:
        logger.error(f"Failed to create checkout session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create checkout session"
        )


@router.get("/portal", response_model=BillingPortalResponse)
async def get_billing_portal(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    return_url: str = "https://sentinel-vla.com/dashboard/settings",
) -> BillingPortalResponse:
    """Get Stripe billing portal URL for customer self-service.

    Args:
        current_user: Current authenticated user
        db: Database session
        return_url: URL to return to after portal session

    Returns:
        BillingPortalResponse with portal URL

    Raises:
        HTTPException: If Stripe is not enabled or customer doesn't have Stripe account
    """
    if not settings.enable_stripe:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe billing is not enabled"
        )

    customer = await get_customer_for_user(current_user, db)

    if not customer.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No billing account found. Please subscribe to a plan first."
        )

    try:
        portal_url = await StripeService.create_billing_portal_session(
            customer_id=customer.stripe_customer_id,
            return_url=return_url,
        )

        return BillingPortalResponse(portal_url=portal_url)
    except StripeError as e:
        logger.error(f"Failed to create billing portal session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to access billing portal"
        )


@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> SubscriptionResponse:
    """Get current subscription information.

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        SubscriptionResponse with subscription details
    """
    customer = await get_customer_for_user(current_user, db)

    cancel_at_period_end = None

    # Get subscription details from Stripe if exists
    if customer.stripe_subscription_id and settings.enable_stripe:
        try:
            subscription_data = await StripeService.get_subscription(
                customer.stripe_subscription_id
            )
            cancel_at_period_end = subscription_data.get("cancel_at_period_end")
        except StripeError as e:
            logger.warning(f"Failed to fetch subscription from Stripe: {e}")

    return SubscriptionResponse(
        subscription_id=customer.stripe_subscription_id,
        status=customer.stripe_subscription_status,
        tier=customer.tier,
        monthly_quota=customer.monthly_quota,
        monthly_usage=customer.monthly_usage,
        cancel_at_period_end=cancel_at_period_end,
    )


@router.post("/webhooks/stripe", response_model=MessageResponse)
async def stripe_webhook(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    stripe_signature: Annotated[str | None, Header(alias="stripe-signature")] = None,
) -> MessageResponse:
    """Handle Stripe webhook events.

    Args:
        request: FastAPI request
        db: Database session
        stripe_signature: Stripe signature header

    Returns:
        Success message

    Raises:
        HTTPException: If signature is invalid or event processing fails
    """
    if not settings.enable_stripe:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe billing is not enabled"
        )

    if not stripe_signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Stripe signature"
        )

    # Get raw body
    payload = await request.body()

    # Verify webhook signature
    try:
        event = StripeService.construct_webhook_event(payload, stripe_signature)
    except ValueError as e:
        logger.error(f"Invalid webhook payload: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payload"
        )
    except Exception as e:
        logger.error(f"Webhook signature verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature"
        )

    # Handle webhook events
    event_type = event["type"]
    logger.info(f"Received Stripe webhook: {event_type}")

    try:
        if event_type == "customer.subscription.created":
            await handle_subscription_created(event["data"]["object"], db)
        elif event_type == "customer.subscription.updated":
            await handle_subscription_updated(event["data"]["object"], db)
        elif event_type == "customer.subscription.deleted":
            await handle_subscription_deleted(event["data"]["object"], db)
        elif event_type == "invoice.payment_succeeded":
            await handle_payment_succeeded(event["data"]["object"], db)
        elif event_type == "invoice.payment_failed":
            await handle_payment_failed(event["data"]["object"], db)
        else:
            logger.info(f"Unhandled webhook event type: {event_type}")

        return MessageResponse(message="Webhook processed successfully")
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook processing failed"
        )


# ============================================================================
# WEBHOOK HANDLERS
# ============================================================================


async def handle_subscription_created(subscription: dict, db: AsyncSession) -> None:
    """Handle subscription.created webhook event."""
    customer_id = subscription["customer"]
    subscription_id = subscription["id"]
    status = subscription["status"]

    logger.info(f"Subscription created: {subscription_id} for customer {customer_id}")

    # Find customer by Stripe customer ID
    result = await db.execute(
        select(Customer).where(Customer.stripe_customer_id == customer_id)
    )
    customer = result.scalar_one_or_none()

    if customer:
        await StripeService.update_customer_subscription(
            db=db,
            customer=customer,
            subscription_id=subscription_id,
            subscription_status=status,
        )


async def handle_subscription_updated(subscription: dict, db: AsyncSession) -> None:
    """Handle subscription.updated webhook event."""
    customer_id = subscription["customer"]
    subscription_id = subscription["id"]
    status = subscription["status"]

    logger.info(f"Subscription updated: {subscription_id} status={status}")

    # Find customer by Stripe customer ID
    result = await db.execute(
        select(Customer).where(Customer.stripe_customer_id == customer_id)
    )
    customer = result.scalar_one_or_none()

    if customer:
        await StripeService.update_customer_subscription(
            db=db,
            customer=customer,
            subscription_id=subscription_id,
            subscription_status=status,
        )


async def handle_subscription_deleted(subscription: dict, db: AsyncSession) -> None:
    """Handle subscription.deleted webhook event."""
    customer_id = subscription["customer"]
    subscription_id = subscription["id"]

    logger.info(f"Subscription deleted: {subscription_id}")

    # Find customer by Stripe customer ID
    result = await db.execute(
        select(Customer).where(Customer.stripe_customer_id == customer_id)
    )
    customer = result.scalar_one_or_none()

    if customer:
        await StripeService.update_customer_subscription(
            db=db,
            customer=customer,
            subscription_id=subscription_id,
            subscription_status="canceled",
        )


async def handle_payment_succeeded(invoice: dict, db: AsyncSession) -> None:
    """Handle invoice.payment_succeeded webhook event."""
    customer_id = invoice["customer"]
    logger.info(f"Payment succeeded for customer {customer_id}")

    # Reset monthly usage if this is a new billing period
    result = await db.execute(
        select(Customer).where(Customer.stripe_customer_id == customer_id)
    )
    customer = result.scalar_one_or_none()

    if customer:
        customer.monthly_usage = 0
        await db.commit()
        logger.info(f"Reset monthly usage for customer {customer.customer_id}")


async def handle_payment_failed(invoice: dict, db: AsyncSession) -> None:
    """Handle invoice.payment_failed webhook event."""
    customer_id = invoice["customer"]
    logger.warning(f"Payment failed for customer {customer_id}")

    # TODO: Send email notification to customer
    # TODO: Implement retry logic or grace period
