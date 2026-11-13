"""
Booking business logic.

Views patle rakhe hain, saari rules/locking/transition logic yahin hai.
"""
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import (
    APIException,
    NotFound,
    PermissionDenied,
    ValidationError,
)

from apps.properties.models import Property

from .models import ACTIVE_BOOKING_STATUSES, Booking

# ---------------------------------------------------------------------------
# Business rule constants
# ---------------------------------------------------------------------------
CHECK_IN_TIME = time(14, 0)          # standard check-in time (local timezone)
MAX_STAY_NIGHTS = 30
MAX_ADVANCE_DAYS = 365

FREE_CANCELLATION_HOURS = 48         # >= 48h pehle: 100% refund
PARTIAL_REFUND_HOURS = 24            # 24h-48h: partial refund
PARTIAL_REFUND_PERCENT = 50          # < 24h: 0%

OVERLAP_CONSTRAINT_NAME = "booking_no_overlap_per_property"

ROLE_GUEST = "guest"
ROLE_HOST = "host"
ROLE_ADMIN = "admin"

# NOTE: plain string values use kiye hain (enum members nahi) taaki dict/set lookup safe rahe.
STATUS_PENDING = Booking.Status.PENDING.value
STATUS_CONFIRMED = Booking.Status.CONFIRMED.value
STATUS_REJECTED = Booking.Status.REJECTED.value
STATUS_CANCELLED = Booking.Status.CANCELLED.value
STATUS_COMPLETED = Booking.Status.COMPLETED.value

# Host/admin ke liye allowed status transitions
STATUS_TRANSITIONS = {
    STATUS_PENDING: {STATUS_CONFIRMED, STATUS_REJECTED},
    STATUS_CONFIRMED: {STATUS_COMPLETED},
}

CANCELLATION_POLICY = {
    "free_cancellation_hours": FREE_CANCELLATION_HOURS,
    "partial_refund_hours": PARTIAL_REFUND_HOURS,
    "partial_refund_percent": PARTIAL_REFUND_PERCENT,
    "summary": (
        f"Pending requests can be cancelled for free. Confirmed bookings: full refund "
        f"up to {FREE_CANCELLATION_HOURS}h before check-in, {PARTIAL_REFUND_PERCENT}% refund "
        f"between {PARTIAL_REFUND_HOURS}h and {FREE_CANCELLATION_HOURS}h, no refund after that."
    ),
}


class BookingConflict(APIException):
    """Dates already booked -> HTTP 409."""

    status_code = 409
    default_detail = "These dates are no longer available for this property."
    default_code = "booking_conflict"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def calculate_total(price_per_night, nights):
    return (Decimal(price_per_night) * nights).quantize(Decimal("0.01"))


def has_overlap(property_id, check_in, check_out):
    """Back-to-back allowed: [check_in, check_out) half-open range."""
    return Booking.objects.filter(
        property_id=property_id,
        status__in=ACTIVE_BOOKING_STATUSES,
        check_in__lt=check_out,
        check_out__gt=check_in,
    ).exists()


def get_check_in_datetime(booking):
    naive = datetime.combine(booking.check_in, CHECK_IN_TIME)
    return timezone.make_aware(naive)


def get_actor_role(booking, user):
    """Is user ka is booking se kya rishta hai? None = koi nahi."""
    if not getattr(user, "is_authenticated", False):
        return None
    if user.is_platform_admin:
        return ROLE_ADMIN
    if booking.guest_id == user.id:
        return ROLE_GUEST
    if booking.property.host_id == user.id:
        return ROLE_HOST
    return None


def _get_locked_booking(booking_id):
    """Booking row ko lock karke laao (sirf booking table lock hoti hai, join wali nahi)."""
    try:
        return (
            Booking.objects.select_for_update(of=("self",))
            .select_related("property")
            .get(pk=booking_id)
        )
    except Booking.DoesNotExist:
        raise NotFound("Booking not found.")


# ---------------------------------------------------------------------------
# Stay rules + quote
# ---------------------------------------------------------------------------
def get_stay_rule_errors(*, property_obj, user, check_in, check_out, num_guests):
    """Business-rule errors ka dict {field: message}. Khali dict = sab theek."""
    errors = {}
    today = timezone.localdate()

    if check_in < today:
        errors["check_in"] = "Check-in date cannot be in the past."
    elif check_in > today + timedelta(days=MAX_ADVANCE_DAYS):
        errors["check_in"] = f"Bookings can be made at most {MAX_ADVANCE_DAYS} days in advance."

    if check_out <= check_in:
        errors["check_out"] = "Check-out date must be after check-in date."
    elif (check_out - check_in).days > MAX_STAY_NIGHTS:
        errors["check_out"] = f"Maximum stay is {MAX_STAY_NIGHTS} nights."

    if num_guests > property_obj.max_guests:
        errors["num_guests"] = f"This property allows at most {property_obj.max_guests} guests."

    if not property_obj.is_active:
        errors["property"] = "This property is not available for booking."
    elif user is not None and property_obj.host_id == getattr(user, "id", None):
        errors["property"] = "You cannot book your own property."

    return errors


def quote_stay(*, property_obj, user, check_in, check_out, num_guests):
    """Availability + price quote. Business-rule fail hone par bhi 200 dete hain (available=False)."""
    errors = get_stay_rule_errors(
        property_obj=property_obj,
        user=user,
        check_in=check_in,
        check_out=check_out,
        num_guests=num_guests,
    )
    if not errors and has_overlap(property_obj.id, check_in, check_out):
        errors["dates"] = "Selected dates are not available."

    nights = max((check_out - check_in).days, 0)
    return {
        "property_id": property_obj.id,
        "check_in": check_in,
        "check_out": check_out,
        "num_guests": num_guests,
        "available": not errors,
        "reasons": list(errors.values()),
        "nights": nights,
        "price_per_night": str(property_obj.price_per_night),
        "total_price": str(calculate_total(property_obj.price_per_night, nights)),
        "currency": "INR",
        "cancellation_policy": CANCELLATION_POLICY,
    }


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------
def create_booking(*, guest, property_id, check_in, check_out, num_guests):
    try:
        with transaction.atomic():
            # 1) Property row lock: same property par concurrent bookings line mein lagengi
            try:
                property_obj = Property.objects.select_for_update().get(pk=property_id)
            except Property.DoesNotExist:
                raise NotFound("Property not found.")

            # 2) Business rules (400)
            errors = get_stay_rule_errors(
                property_obj=property_obj,
                user=guest,
                check_in=check_in,
                check_out=check_out,
                num_guests=num_guests,
            )
            if errors:
                raise ValidationError(errors)

            # 3) Overlap check (lock ke andar, isliye race-free) -> 409
            if has_overlap(property_obj.id, check_in, check_out):
                raise BookingConflict()

            # 4) Price snapshot ke saath create
            nights = (check_out - check_in).days
            booking = Booking.objects.create(
                guest=guest,
                property=property_obj,
                check_in=check_in,
                check_out=check_out,
                num_guests=num_guests,
                price_per_night=property_obj.price_per_night,
                total_price=calculate_total(property_obj.price_per_night, nights),
                status=STATUS_PENDING,
            )
    except IntegrityError as exc:
        # Final guard: DB ExclusionConstraint ne double-booking roki
        if OVERLAP_CONSTRAINT_NAME in str(exc):
            raise BookingConflict() from exc
        raise
    return booking


# ---------------------------------------------------------------------------
# Status change (host / admin)
# ---------------------------------------------------------------------------
def change_status(*, booking_id, actor, new_status, reason=""):
    with transaction.atomic():
        booking = _get_locked_booking(booking_id)

        role = get_actor_role(booking, actor)
        if role not in (ROLE_HOST, ROLE_ADMIN):
            raise PermissionDenied("Only the property host or an admin can change the booking status.")

        allowed = STATUS_TRANSITIONS.get(booking.status, set())
        if new_status not in allowed:
            raise ValidationError(
                {"status": f"Cannot change booking from '{booking.status}' to '{new_status}'."}
            )

        today = timezone.localdate()
        if new_status == STATUS_CONFIRMED and booking.check_in < today:
            raise ValidationError(
                {"status": "Cannot confirm a booking whose check-in date has already passed."}
            )
        if new_status == STATUS_COMPLETED and booking.check_out > today:
            raise ValidationError(
                {"status": "A booking can be completed only after the stay has ended."}
            )

        booking.status = new_status
        update_fields = ["status", "updated_at"]
        if new_status == STATUS_REJECTED and reason:
            booking.cancellation_reason = reason  # reject reason isi field mein
            update_fields.append("cancellation_reason")
        booking.save(update_fields=update_fields)
    return booking


# ---------------------------------------------------------------------------
# Cancellation
# ---------------------------------------------------------------------------
def get_cancel_block_reason(booking, role, now):
    """None = cancel ho sakta hai, warna reason string."""
    if booking.status not in ACTIVE_BOOKING_STATUSES:
        return f"A {booking.status} booking cannot be cancelled."
    if role == ROLE_HOST and booking.status == STATUS_PENDING:
        return "Pending requests should be rejected, not cancelled. Use the status endpoint."
    if now >= get_check_in_datetime(booking):
        return "The stay has already started, so this booking can no longer be cancelled."
    return None


def get_refund_percentage(booking, role, now):
    if role != ROLE_GUEST:
        return 100  # host/admin cancel -> guest ko full refund
    if booking.status == STATUS_PENDING:
        return 100  # host ne abhi confirm hi nahi kiya
    hours_before = (get_check_in_datetime(booking) - now).total_seconds() / 3600
    if hours_before >= FREE_CANCELLATION_HOURS:
        return 100
    if hours_before >= PARTIAL_REFUND_HOURS:
        return PARTIAL_REFUND_PERCENT
    return 0


def cancel_booking(*, booking_id, actor, reason="", now=None):
    now = now or timezone.now()
    with transaction.atomic():
        booking = _get_locked_booking(booking_id)

        role = get_actor_role(booking, actor)
        if role is None:
            raise PermissionDenied("You are not allowed to cancel this booking.")

        block_reason = get_cancel_block_reason(booking, role, now)
        if block_reason:
            raise ValidationError({"detail": block_reason})

        reason = (reason or "").strip()
        if role != ROLE_GUEST and not reason:
            raise ValidationError(
                {"reason": "A cancellation reason is required for host/admin cancellations."}
            )

        refund_percentage = get_refund_percentage(booking, role, now)

        booking.status = STATUS_CANCELLED
        booking.cancelled_at = now
        booking.cancellation_reason = reason
        booking.save(update_fields=["status", "cancelled_at", "cancellation_reason", "updated_at"])
    return booking, refund_percentage


# ---------------------------------------------------------------------------
# Frontend helper: user is booking par kaun se actions le sakta hai
# ---------------------------------------------------------------------------
def get_available_actions(booking, user):
    role = get_actor_role(booking, user)
    if role is None:
        return []

    actions = []
    today = timezone.localdate()

    if role in (ROLE_HOST, ROLE_ADMIN):
        if booking.status == STATUS_PENDING:
            if booking.check_in >= today:
                actions.append("confirm")
            actions.append("reject")
        elif booking.status == STATUS_CONFIRMED and booking.check_out <= today:
            actions.append("complete")

    if get_cancel_block_reason(booking, role, timezone.now()) is None:
        actions.append("cancel")
    return actions