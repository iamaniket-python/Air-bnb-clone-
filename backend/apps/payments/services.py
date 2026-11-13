"""
Payment business logic.

Rules:
- Sirf confirmed booking ka guest pay kar sakta hai.
- Amount hamesha booking.total_price se (client se kabhi nahi).
- Signature server par verify hota hai.
- Failure state ko commit karne ke liye error atomic block ke BAAD raise karte hain
  (warna exception transaction rollback kar deti aur "failed" mark gayab ho jaata).
"""
import uuid
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import APIException, NotFound, ValidationError

from apps.bookings.models import Booking

from . import gateways
from .models import Payment

CURRENCY = "INR"

STATUS_PENDING = Payment.Status.PENDING.value
STATUS_SUCCESS = Payment.Status.SUCCESS.value
STATUS_FAILED = Payment.Status.FAILED.value
STATUS_REFUNDED = Payment.Status.REFUNDED.value
BOOKING_CONFIRMED = Booking.Status.CONFIRMED.value


class PaymentConflict(APIException):
    status_code = 409
    default_detail = "Payment conflict."
    default_code = "payment_conflict"


class PaymentDeclined(APIException):
    status_code = 402
    default_detail = "Payment was declined by the gateway."
    default_code = "payment_declined"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _get_payment_for_guest(transaction_id, user, lock=False):
    queryset = Payment.objects.select_related("booking", "booking__property")
    if lock:
        queryset = queryset.select_for_update(of=("self",))
    try:
        return queryset.get(transaction_id=transaction_id, booking__guest=user)
    except Payment.DoesNotExist:
        raise NotFound("Payment not found.")


def _mark_failed(payment, reason):
    payment.status = STATUS_FAILED
    payment.failure_reason = reason
    payment.save(update_fields=["status", "failure_reason", "updated_at"])


def get_checkout_payload(payment):
    """Frontend ko gateway checkout kholne ke liye jo chahiye (koi secret nahi)."""
    return {
        "provider": payment.provider,
        "order_id": payment.provider_order_id,
        "amount": str(payment.amount),
        "currency": payment.currency,
    }


# ---------------------------------------------------------------------------
# Create order
# ---------------------------------------------------------------------------
def create_payment(*, booking_id, user):
    """Returns (payment, created). Pehle se pending payment ho to wahi reuse hota hai."""
    with transaction.atomic():
        try:
            booking = (
                Booking.objects.select_for_update(of=("self",))
                .select_related("property")
                .get(pk=booking_id, guest=user)
            )
        except Booking.DoesNotExist:
            raise NotFound("Booking not found.")

        if booking.status != BOOKING_CONFIRMED:
            raise ValidationError(
                {
                    "booking": "Payment is possible only for confirmed bookings "
                    f"(current status: {booking.status})."
                }
            )
        if booking.check_in < timezone.localdate():
            raise ValidationError(
                {"booking": "Check-in date has passed; payment is no longer possible."}
            )
        if booking.payments.filter(status=STATUS_SUCCESS).exists():
            raise PaymentConflict("This booking is already paid.")

        existing = booking.payments.filter(status=STATUS_PENDING).first()
        if existing:
            return existing, False

        gateway = gateways.get_gateway(gateways.get_default_provider())
        payment = Payment.objects.create(
            booking=booking,
            amount=booking.total_price,  # server-side amount, client se nahi
            currency=CURRENCY,
            provider=gateway.name,
            status=STATUS_PENDING,
        )
        order = gateway.create_order(payment)
        payment.provider_order_id = order["order_id"]
        payment.raw_response = {"order": order["raw"]}
        payment.save(update_fields=["provider_order_id", "raw_response", "updated_at"])
    return payment, True


# ---------------------------------------------------------------------------
# Verify (server-side signature check)
# ---------------------------------------------------------------------------
def verify_payment(*, transaction_id, user, provider_payment_id, signature):
    """Returns (payment, newly_verified)."""
    error = None
    try:
        with transaction.atomic():
            payment = _get_payment_for_guest(transaction_id, user, lock=True)

            if payment.status == STATUS_SUCCESS:
                if payment.provider_payment_id == provider_payment_id:
                    return payment, False  # idempotent: dobara verify safe hai
                raise PaymentConflict("This payment is already completed.")

            if payment.status != STATUS_PENDING:
                raise ValidationError(
                    {"detail": f"This payment is {payment.status}. Please start a new payment."}
                )

            # Replay protection: ye gateway payment id kisi aur payment par use ho chuka?
            if (
                Payment.objects.filter(provider_payment_id=provider_payment_id)
                .exclude(pk=payment.pk)
                .exists()
            ):
                raise ValidationError(
                    {"provider_payment_id": "This payment id has already been used."}
                )

            gateway = gateways.get_gateway(payment.provider)
            if not gateway.verify_signature(
                order_id=payment.provider_order_id,
                payment_id=provider_payment_id,
                signature=signature,
            ):
                _mark_failed(payment, "Signature verification failed.")
                error = ValidationError({"signature": "Invalid payment signature."})
            elif payment.booking.status != BOOKING_CONFIRMED:
                _mark_failed(payment, "Booking is no longer payable.")
                error = PaymentConflict("Booking is no longer payable.")
            else:
                now = timezone.now()
                raw = dict(payment.raw_response or {})
                raw["verification"] = {
                    "verified_at": now.isoformat(),
                    "provider_payment_id": provider_payment_id,
                }
                payment.status = STATUS_SUCCESS
                payment.provider_payment_id = provider_payment_id
                payment.provider_signature = signature
                payment.paid_at = now
                payment.raw_response = raw
                payment.save(
                    update_fields=[
                        "status",
                        "provider_payment_id",
                        "provider_signature",
                        "paid_at",
                        "raw_response",
                        "updated_at",
                    ]
                )
    except IntegrityError as exc:
        # DB constraints (ek booking par ek success / unique provider_payment_id) final guard
        raise PaymentConflict("Duplicate payment detected for this booking.") from exc

    if error:
        raise error
    return payment, True


# ---------------------------------------------------------------------------
# Mock gateway simulation (sirf dev/test; view mein flag se gated)
# ---------------------------------------------------------------------------
def simulate_mock_checkout(*, transaction_id, user, outcome):
    """
    Real gateway ka kaam simulate karta hai. Card details yahan KABHI nahi aati,
    sirf outcome (success/failure).
    """
    declined = False
    result = {}
    with transaction.atomic():
        payment = _get_payment_for_guest(transaction_id, user, lock=True)
        if payment.provider != "mock":
            raise ValidationError({"detail": "This payment does not use the mock provider."})
        if payment.status != STATUS_PENDING:
            raise ValidationError({"detail": f"This payment is already {payment.status}."})

        gateway = gateways.get_gateway(payment.provider)
        if outcome == "failure":
            _mark_failed(payment, "Payment declined by mock gateway.")
            declined = True
        else:
            provider_payment_id = f"mock_pay_{uuid.uuid4().hex[:16]}"
            result = {
                "outcome": "success",
                "transaction_id": str(payment.transaction_id),
                "provider_order_id": payment.provider_order_id,
                "provider_payment_id": provider_payment_id,
                "signature": gateway.sign(payment.provider_order_id, provider_payment_id),
            }

    if declined:
        raise PaymentDeclined("Payment was declined by the mock gateway.")
    return result


# ---------------------------------------------------------------------------
# Booking cancel hook (bookings.services.cancel_booking se call hota hai)
# ---------------------------------------------------------------------------
@transaction.atomic
def process_booking_cancellation(booking, refund_percentage):
    """
    - Pending payments -> failed
    - Success payment -> refund_percentage ke hisaab se refund
    Returns refunded/updated payment ya None.
    """
    now = timezone.now()

    Payment.objects.filter(booking=booking, status=STATUS_PENDING).update(
        status=STATUS_FAILED,
        failure_reason="Booking was cancelled.",
        updated_at=now,
    )

    payment = (
        Payment.objects.select_for_update()
        .filter(booking=booking, status=STATUS_SUCCESS)
        .first()
    )
    if payment is None:
        return None

    amount = (payment.amount * Decimal(refund_percentage) / Decimal(100)).quantize(
        Decimal("0.01")
    )
    raw = dict(payment.raw_response or {})

    if amount > 0:
        gateway = gateways.get_gateway(payment.provider)
        refund = gateway.refund(payment, amount)
        raw["refund"] = {
            "percentage": refund_percentage,
            "amount": str(amount),
            "refund_id": refund["refund_id"],
            "refunded_at": now.isoformat(),
        }
        payment.status = STATUS_REFUNDED
    else:
        # 0% refund: payment success hi rehta hai, bas record kar dete hain
        raw["refund"] = {
            "percentage": 0,
            "amount": "0.00",
            "refund_id": None,
            "refunded_at": None,
        }

    payment.raw_response = raw
    payment.save(update_fields=["status", "raw_response", "updated_at"])
    return payment