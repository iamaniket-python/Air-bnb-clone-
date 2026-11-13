"""
Payment gateway abstraction (Strategy pattern).

Naya provider (Razorpay/Stripe) add karna ho to PaymentGateway ke 3 methods implement karo
aur GATEWAYS dict mein register karo. Baaki code (services/views) badalta nahi.
"""
import hashlib
import hmac
import uuid
from abc import ABC, abstractmethod

from django.conf import settings


class PaymentGateway(ABC):
    name = ""

    @abstractmethod
    def create_order(self, payment):
        """Return {"order_id": str, "raw": dict}"""

    @abstractmethod
    def verify_signature(self, *, order_id, payment_id, signature):
        """Server-side signature verification. Return bool."""

    @abstractmethod
    def refund(self, payment, amount):
        """Return {"refund_id": str}"""


class MockGateway(PaymentGateway):
    """
    Fake gateway, real flow jaisa: HMAC_SHA256(secret, "order_id|payment_id").
    Razorpay ki signature scheme bhi yahi hoti hai (apni key_secret ke saath).
    """

    name = "mock"

    def _secret(self):
        # Alag secret/env var ki zaroorat nahi: SECRET_KEY se derive karte hain
        return f"{settings.SECRET_KEY}:mock-gateway".encode()

    def sign(self, order_id, payment_id):
        message = f"{order_id}|{payment_id}".encode()
        return hmac.new(self._secret(), message, hashlib.sha256).hexdigest()

    def create_order(self, payment):
        order_id = f"mock_order_{uuid.uuid4().hex[:20]}"
        return {
            "order_id": order_id,
            "raw": {
                "id": order_id,
                "amount": str(payment.amount),
                "currency": payment.currency,
                "status": "created",
            },
        }

    def verify_signature(self, *, order_id, payment_id, signature):
        expected = self.sign(order_id, payment_id)
        # constant-time compare (timing attack se bachne ke liye)
        return hmac.compare_digest(expected.encode(), (signature or "").encode())

    def refund(self, payment, amount):
        return {"refund_id": f"mock_rfnd_{uuid.uuid4().hex[:16]}"}


GATEWAYS = {
    MockGateway.name: MockGateway,
    # "razorpay": RazorpayGateway,   # future
}


def get_gateway(provider):
    try:
        return GATEWAYS[provider]()
    except KeyError:
        raise ValueError(f"Unsupported payment provider: {provider}")


def get_default_provider():
    return getattr(settings, "PAYMENT_PROVIDER", "mock")


def is_mock_enabled():
    """Mock checkout sirf dev/test mein. Production mein DEBUG=False hota hai, to band."""
    return bool(getattr(settings, "PAYMENT_MOCK_ENABLED", settings.DEBUG))