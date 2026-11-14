from datetime import date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import (
    Avg,
    Case,
    Count,
    DecimalField,
    ExpressionWrapper,
    F,
    Q,
    Sum,
    Value,
    When,
)
from django.db.models.fields.json import KT
from django.db.models.functions import Cast, Coalesce, TruncMonth
from django.utils import timezone

from apps.accounts.services import blacklist_all_tokens
from apps.bookings.models import ACTIVE_BOOKING_STATUSES, Booking
from apps.payments.models import Payment
from apps.properties.models import Property
from apps.reviews.models import Review

User = get_user_model()

# Plain strings (lesson 1: enum members dict/hash lookup mein nahi)
BOOKING_PENDING = "pending"
PAYMENT_SUCCESS = "success"
PAYMENT_REFUNDED = "refunded"
EARNING_STATUSES = [PAYMENT_SUCCESS, PAYMENT_REFUNDED]

CURRENCY = "INR"
MONTHS_WINDOW = 6
NEXT_RESERVATIONS_LIMIT = 5
NEW_USERS_WINDOW_DAYS = 30

MONEY = DecimalField(max_digits=12, decimal_places=2)
ZERO = Decimal("0.00")
TWO_PLACES = Decimal("0.01")


# ---------------------------------------------------------------- helpers
def money(value):
    value = Decimal(str(value)) if value is not None else ZERO
    return f"{value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP):.2f}"


def rating_value(value):
    if value is None:
        return "0.00"
    return money(value)


def status_breakdown(qs, statuses):
    """{status: count}, saare statuses zero-filled, keys plain strings."""
    counts = {
        row["status"]: row["n"]
        for row in qs.values("status").annotate(n=Count("id")).order_by()
    }
    return {s: counts.get(s, 0) for s in statuses}


def shift_month(first_of_month, delta):
    idx = first_of_month.year * 12 + (first_of_month.month - 1) + delta
    return date(idx // 12, idx % 12 + 1, 1)


def last_months(today, n=MONTHS_WINDOW):
    current = today.replace(day=1)
    return [shift_month(current, -i) for i in range(n - 1, -1, -1)]


def with_net_amount(payments_qs):
    """
    success + refunded payments par refunded_amount aur net_amount annotate.
    refund amount raw_response["refund"]["amount"] se (DB level cast).
    Refunded status par amount missing ho to full refund maana jaata hai.
    """
    refund_text = KT("raw_response__refund__amount")
    fallback = Case(
        When(status=PAYMENT_REFUNDED, then=F("amount")),
        default=Value(ZERO),
        output_field=MONEY,
    )
    return (
        payments_qs.filter(status__in=EARNING_STATUSES)
        .annotate(
            refunded_amount=Coalesce(
                Cast(refund_text, MONEY), fallback, output_field=MONEY
            )
        )
        .annotate(
            net_amount=ExpressionWrapper(
                F("amount") - F("refunded_amount"), output_field=MONEY
            )
        )
    )


def monthly_earnings(payments_qs, today):
    months = last_months(today)
    start = timezone.make_aware(datetime.combine(months[0], time.min))
    rows = (
        with_net_amount(payments_qs)
        .filter(paid_at__gte=start)
        .annotate(month=TruncMonth("paid_at"))
        .values("month")
        .annotate(amount=Sum("net_amount"))
        .order_by("month")
    )
    by_month = {row["month"].strftime("%Y-%m"): row["amount"] for row in rows}
    return [
        {"month": m.strftime("%Y-%m"), "amount": money(by_month.get(m.strftime("%Y-%m")))}
        for m in months
    ]


# ---------------------------------------------------------------- host
def get_host_dashboard(host, today=None):
    today = today or timezone.localdate()

    props = Property.objects.filter(host=host).aggregate(
        total=Count("id"),
        active=Count("id", filter=Q(is_active=True)),
    )

    bookings = Booking.objects.filter(property__host=host)
    upcoming_q = Q(status__in=ACTIVE_BOOKING_STATUSES, check_in__gte=today)
    booking_stats = bookings.aggregate(
        total=Count("id"),
        upcoming=Count("id", filter=upcoming_q),
        pending=Count(
            "id", filter=Q(status=BOOKING_PENDING, check_in__gte=today)
        ),
    )

    payments = Payment.objects.filter(booking__property__host=host)
    total_earnings = with_net_amount(payments).aggregate(
        total=Coalesce(Sum("net_amount"), Value(ZERO), output_field=MONEY)
    )["total"]
    monthly = monthly_earnings(payments, today)

    review_stats = Review.objects.filter(booking__property__host=host).aggregate(
        count=Count("id"), avg=Avg("rating")
    )

    next_reservations = list(
        bookings.filter(upcoming_q)
        .select_related("guest", "property")
        .order_by("check_in", "id")[:NEXT_RESERVATIONS_LIMIT]
    )

    return {
        "properties": {
            "total": props["total"],
            "active": props["active"],
            "inactive": props["total"] - props["active"],
        },
        "bookings": {
            "total": booking_stats["total"],
            "upcoming_reservations": booking_stats["upcoming"],
            "pending_requests": booking_stats["pending"],
            "by_status": status_breakdown(bookings, Booking.Status.values),
        },
        "earnings": {
            "currency": CURRENCY,
            "total": money(total_earnings),
            "this_month": monthly[-1]["amount"],
            "monthly": monthly,
        },
        "reviews": {
            "count": review_stats["count"],
            "average_rating": rating_value(review_stats["avg"]),
        },
        "next_reservations": next_reservations,
    }


# ---------------------------------------------------------------- admin
def get_admin_dashboard(today=None):
    today = today or timezone.localdate()
    since = timezone.now() - timedelta(days=NEW_USERS_WINDOW_DAYS)

    user_stats = User.objects.aggregate(
        total=Count("id"),
        active=Count("id", filter=Q(is_active=True)),
        new=Count("id", filter=Q(date_joined__gte=since)),
    )
    roles = {
        row["role"]: row["n"]
        for row in User.objects.values("role").annotate(n=Count("id")).order_by()
    }

    prop_stats = Property.objects.aggregate(
        total=Count("id"), active=Count("id", filter=Q(is_active=True))
    )

    bookings = Booking.objects.all()
    booking_stats = bookings.aggregate(
        total=Count("id"),
        upcoming=Count(
            "id", filter=Q(status__in=ACTIVE_BOOKING_STATUSES, check_in__gte=today)
        ),
        recent=Count("id", filter=Q(created_at__gte=since)),
    )

    review_stats = Review.objects.aggregate(count=Count("id"), avg=Avg("rating"))

    payments = Payment.objects.all()
    revenue = with_net_amount(payments).aggregate(
        gross=Coalesce(Sum("amount"), Value(ZERO), output_field=MONEY),
        refunded=Coalesce(Sum("refunded_amount"), Value(ZERO), output_field=MONEY),
        net=Coalesce(Sum("net_amount"), Value(ZERO), output_field=MONEY),
    )

    return {
        "users": {
            "total": user_stats["total"],
            "active": user_stats["active"],
            "inactive": user_stats["total"] - user_stats["active"],
            "new_last_30_days": user_stats["new"],
            "by_role": {r: roles.get(r, 0) for r in User.Role.values},
        },
        "properties": {
            "total": prop_stats["total"],
            "active": prop_stats["active"],
            "inactive": prop_stats["total"] - prop_stats["active"],
        },
        "bookings": {
            "total": booking_stats["total"],
            "upcoming": booking_stats["upcoming"],
            "created_last_30_days": booking_stats["recent"],
            "by_status": status_breakdown(bookings, Booking.Status.values),
        },
        "reviews": {
            "count": review_stats["count"],
            "average_rating": rating_value(review_stats["avg"]),
        },
        "payments": {
            "currency": CURRENCY,
            "gross": money(revenue["gross"]),
            "refunded": money(revenue["refunded"]),
            "net": money(revenue["net"]),
            "by_status": status_breakdown(payments, Payment.Status.values),
        },
        "generated_at": timezone.now(),
    }


# ---------------------------------------------------------------- admin actions
def set_user_active(user, is_active):
    with transaction.atomic():
        User.objects.filter(pk=user.pk).update(is_active=is_active)
        user.is_active = is_active
    if not is_active:
        blacklist_all_tokens(user)
    return user


def set_property_active(prop, is_active):
    # .update(): clean()/save() side-effects nahi, sirf listing toggle
    Property.objects.filter(pk=prop.pk).update(
        is_active=is_active, updated_at=timezone.now()
    )
    prop.is_active = is_active
    return prop