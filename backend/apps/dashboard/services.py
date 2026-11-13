from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Avg, Count, Sum
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from apps.accounts.models import User
from apps.accounts.services import blacklist_all_tokens
from apps.bookings.models import Booking
from apps.payments.models import Payment
from apps.properties.models import Property
from apps.reviews.models import Review

# Plain strings (lesson 1: enum ko dict key mat banao)
BOOKING_STATUSES = ["pending", "confirmed", "rejected", "cancelled", "completed"]
ROLES = ["guest", "host", "admin"]
PAYMENT_STATUSES = ["pending", "success", "failed", "refunded"]
PAID_STATUSES = ["success", "refunded"]
UPCOMING_STATUSES = ["pending", "confirmed"]
ASSIGNABLE_ROLES = ["guest", "host"]
RECENT_BOOKINGS_LIMIT = 5
NEW_USERS_WINDOW_DAYS = 30
ZERO = Decimal("0.00")
CENT = Decimal("0.01")


# ---------------------------------------------------------------- helpers
def money(value):
    """Decimal -> '1234.50' string."""
    return str(Decimal(value).quantize(CENT))


def to_decimal(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return ZERO


def breakdown(queryset, field, keys):
    """{key: count} sab keys ke saath (0 default). order_by() zaroori hai (GROUP BY)."""
    counts = {key: 0 for key in keys}
    rows = queryset.order_by().values(field).annotate(n=Count("id"))
    for row in rows:
        counts[row[field]] = row["n"]
    return counts


def calculate_earnings(payments):
    """
    payments: Payment queryset (host ki ya poore platform ki).
    gross    = success + refunded payments ka amount
    refunded = sirf refunded payments ke raw_response["refund"]["amount"]
    net      = gross - refunded
    """
    gross = (
        payments.filter(status__in=PAID_STATUSES).aggregate(total=Sum("amount"))["total"]
        or ZERO
    )
    refunded = ZERO
    for raw in payments.filter(status="refunded").values_list("raw_response", flat=True):
        refund = raw.get("refund") if isinstance(raw, dict) else None
        if isinstance(refund, dict):
            refunded += to_decimal(refund.get("amount", 0))
    return {
        "gross": money(gross),
        "refunded": money(refunded),
        "net": money(gross - refunded),
        "currency": "INR",
    }


# ----------------------------------------------------------- host dashboard
def get_host_dashboard(host, today=None):
    today = today or timezone.localdate()

    properties = Property.objects.filter(host=host)
    bookings = Booking.objects.filter(property__host=host)
    payments = Payment.objects.filter(booking__property__host=host)

    recent = bookings.select_related("property", "guest").order_by("-created_at", "-id")[
        :RECENT_BOOKINGS_LIMIT
    ]

    return {
        "properties": {
            "total": properties.count(),
            "active": properties.filter(is_active=True).count(),
        },
        "bookings": {
            "total": bookings.count(),
            "upcoming_reservations": bookings.filter(
                status__in=UPCOMING_STATUSES, check_in__gte=today
            ).count(),
            "pending_requests": bookings.filter(status="pending").count(),
            "by_status": breakdown(bookings, "status", BOOKING_STATUSES),
        },
        "earnings": calculate_earnings(payments),
        "recent_bookings": [
            {
                "id": b.id,
                "property_id": b.property_id,
                "property_title": b.property.title,
                "guest_username": b.guest.username,
                "check_in": b.check_in.isoformat(),
                "check_out": b.check_out.isoformat(),
                "status": b.status,
                "total_price": money(b.total_price),
            }
            for b in recent
        ],
    }


# ---------------------------------------------------------- admin dashboard
def get_admin_dashboard(now=None):
    now = now or timezone.now()
    since = now - timedelta(days=NEW_USERS_WINDOW_DAYS)

    users = User.objects.all()
    properties = Property.objects.all()
    bookings = Booking.objects.all()
    payments = Payment.objects.all()
    review_stats = Review.objects.aggregate(total=Count("id"), avg=Avg("rating"))
    avg = review_stats["avg"]

    return {
        "users": {
            "total": users.count(),
            "by_role": breakdown(users, "role", ROLES),
            "inactive": users.filter(is_active=False).count(),
            "new_last_30_days": users.filter(date_joined__gte=since).count(),
        },
        "properties": {
            "total": properties.count(),
            "active": properties.filter(is_active=True).count(),
        },
        "bookings": {
            "total": bookings.count(),
            "by_status": breakdown(bookings, "status", BOOKING_STATUSES),
        },
        "reviews": {
            "total": review_stats["total"] or 0,
            "average_rating": money(to_decimal(avg)) if avg is not None else "0.00",
        },
        "payments": {
            "by_status": breakdown(payments, "status", PAYMENT_STATUSES),
            "revenue": calculate_earnings(payments),
        },
    }


# -------------------------------------------------------- admin: users
def update_user(actor, user_id, *, is_active=None, role=None):
    try:
        target = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        raise NotFound("User not found.")

    if target.pk == actor.pk:
        raise ValidationError({"detail": ["You cannot modify your own account here."]})
    if target.is_superuser or target.role == "admin":
        raise ValidationError({"detail": ["Admin accounts cannot be modified here."]})

    if role is not None and role != target.role:
        if role not in ASSIGNABLE_ROLES:
            raise ValidationError({"role": ["Role must be 'guest' or 'host'."]})
        if role != "host" and target.properties.exists():
            raise ValidationError(
                {"role": ["This host still has properties. Deactivate or remove them first."]}
            )

    with transaction.atomic():
        target = User.objects.select_for_update().get(pk=user_id)
        fields = []
        if is_active is not None and is_active != target.is_active:
            target.is_active = is_active
            fields.append("is_active")
        if role is not None and role != target.role:
            target.role = role
            fields.append("role")
        if fields:
            target.save(update_fields=fields)
        if "is_active" in fields and not target.is_active:
            blacklist_all_tokens(target)  # deactivate par saare refresh tokens bekaar
    return target


# ---------------------------------------------------- admin: properties
def set_property_active(property_id, is_active):
    try:
        prop = Property.objects.get(pk=property_id)
    except Property.DoesNotExist:
        raise NotFound("Property not found.")
    if prop.is_active != is_active:
        prop.is_active = is_active
        prop.save(update_fields=["is_active", "updated_at"])
    return prop