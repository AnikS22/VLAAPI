"""Stripe billing integration service."""

import logging
from typing import Optional

import stripe
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.models.database import Customer

settings = get_settings()
logger = logging.getLogger(__name__)

# Initialize Stripe with API key
if settings.stripe_api_key:
    stripe.api_key = settings.stripe_api_key


class StripeService:
    """Service for Stripe billing operations."""

    @staticmethod
    async def create_customer(
        email: str,
        name: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> str:
        """Create a Stripe customer.

        Args:
            email: Customer email
            name: Customer name
            metadata: Additional metadata

        Returns:
            Stripe customer ID

        Raises:
            stripe.error.StripeError: If Stripe API call fails
        """
        if not settings.enable_stripe:
            raise ValueError("Stripe integration is not enabled")

        customer_data = {
            "email": email,
            "metadata": metadata or {},
        }

        if name:
            customer_data["name"] = name

        stripe_customer = stripe.Customer.create(**customer_data)
        logger.info(f"Created Stripe customer: {stripe_customer.id} for {email}")

        return stripe_customer.id

    @staticmethod
    async def create_checkout_session(
        customer_id: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
        metadata: Optional[dict] = None,
    ) -> dict:
        """Create a Stripe Checkout session for subscription.

        Args:
            customer_id: Stripe customer ID
            price_id: Stripe price ID (for Pro or Enterprise tier)
            success_url: URL to redirect after successful payment
            cancel_url: URL to redirect if payment is cancelled
            metadata: Additional metadata

        Returns:
            Checkout session dict with URL and session ID

        Raises:
            stripe.error.StripeError: If Stripe API call fails
        """
        if not settings.enable_stripe:
            raise ValueError("Stripe integration is not enabled")

        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{
                "price": price_id,
                "quantity": 1,
            }],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata=metadata or {},
        )

        logger.info(f"Created Stripe checkout session: {session.id}")

        return {
            "session_id": session.id,
            "url": session.url,
        }

    @staticmethod
    async def create_billing_portal_session(
        customer_id: str,
        return_url: str,
    ) -> str:
        """Create a Stripe billing portal session for customer self-service.

        Args:
            customer_id: Stripe customer ID
            return_url: URL to return to after portal session

        Returns:
            Billing portal URL

        Raises:
            stripe.error.StripeError: If Stripe API call fails
        """
        if not settings.enable_stripe:
            raise ValueError("Stripe integration is not enabled")

        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )

        logger.info(f"Created billing portal session for customer: {customer_id}")

        return session.url

    @staticmethod
    async def get_subscription(subscription_id: str) -> dict:
        """Get subscription details from Stripe.

        Args:
            subscription_id: Stripe subscription ID

        Returns:
            Subscription data dict

        Raises:
            stripe.error.StripeError: If Stripe API call fails
        """
        if not settings.enable_stripe:
            raise ValueError("Stripe integration is not enabled")

        subscription = stripe.Subscription.retrieve(subscription_id)

        return {
            "id": subscription.id,
            "status": subscription.status,
            "current_period_end": subscription.current_period_end,
            "cancel_at_period_end": subscription.cancel_at_period_end,
            "items": [
                {
                    "price_id": item.price.id,
                    "product_id": item.price.product,
                }
                for item in subscription["items"].data
            ],
        }

    @staticmethod
    async def cancel_subscription(subscription_id: str) -> dict:
        """Cancel a subscription at period end.

        Args:
            subscription_id: Stripe subscription ID

        Returns:
            Updated subscription data

        Raises:
            stripe.error.StripeError: If Stripe API call fails
        """
        if not settings.enable_stripe:
            raise ValueError("Stripe integration is not enabled")

        subscription = stripe.Subscription.modify(
            subscription_id,
            cancel_at_period_end=True,
        )

        logger.info(f"Cancelled subscription: {subscription_id}")

        return {
            "id": subscription.id,
            "status": subscription.status,
            "cancel_at_period_end": subscription.cancel_at_period_end,
        }

    @staticmethod
    async def update_customer_subscription(
        db: AsyncSession,
        customer: Customer,
        subscription_id: str,
        subscription_status: str,
    ) -> None:
        """Update customer's subscription information in database.

        Args:
            db: Database session
            customer: Customer object
            subscription_id: Stripe subscription ID
            subscription_status: Subscription status
        """
        customer.stripe_subscription_id = subscription_id
        customer.stripe_subscription_status = subscription_status

        # Update tier based on subscription status
        if subscription_status == "active":
            # Determine tier from subscription price ID
            subscription = await StripeService.get_subscription(subscription_id)

            for item in subscription["items"]:
                if item["price_id"] == settings.stripe_price_id_pro:
                    customer.tier = "pro"
                    customer.rate_limit_rpm = settings.rate_limit_pro_rpm
                    customer.rate_limit_rpd = settings.rate_limit_pro_rpd
                    customer.monthly_quota = settings.rate_limit_pro_monthly
                elif item["price_id"] == settings.stripe_price_id_enterprise:
                    customer.tier = "enterprise"
                    customer.rate_limit_rpm = settings.rate_limit_enterprise_rpm
                    customer.rate_limit_rpd = settings.rate_limit_enterprise_rpd
                    customer.monthly_quota = settings.rate_limit_enterprise_monthly
        elif subscription_status in ("canceled", "past_due", "unpaid"):
            # Downgrade to free tier
            customer.tier = "free"
            customer.rate_limit_rpm = settings.rate_limit_free_rpm
            customer.rate_limit_rpd = settings.rate_limit_free_rpd
            customer.monthly_quota = settings.rate_limit_free_monthly

        await db.commit()
        logger.info(
            f"Updated customer {customer.customer_id} subscription: "
            f"{subscription_status}, tier: {customer.tier}"
        )

    @staticmethod
    def construct_webhook_event(
        payload: bytes,
        sig_header: str,
    ) -> stripe.Event:
        """Construct and verify a Stripe webhook event.

        Args:
            payload: Raw request body
            sig_header: Stripe-Signature header

        Returns:
            Verified Stripe Event object

        Raises:
            stripe.error.SignatureVerificationError: If signature is invalid
            ValueError: If webhook secret is not configured
        """
        if not settings.stripe_webhook_secret:
            raise ValueError("Stripe webhook secret is not configured")

        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            settings.stripe_webhook_secret,
        )

        return event
