import django_filters
from django.db.models import Q
from django.utils import timezone

from .models import ACTIVE_BOOKING_STATUSES, Booking


class BookingFilter(django_filters.FilterSet):
    status = django_filters.MultipleChoiceFilter(choices=Booking.Status.choices)
    upcoming = django_filters.BooleanFilter(method="filter_upcoming")
    property = django_filters.NumberFilter(field_name="property_id")
    check_in_from = django_filters.DateFilter(field_name="check_in", lookup_expr="gte")
    check_in_to = django_filters.DateFilter(field_name="check_in", lookup_expr="lte")

    class Meta:
        model = Booking
        fields = []

    def filter_upcoming(self, queryset, name, value):
        """upcoming=true: pending/confirmed aur check_in aaj ya aage. false: baaki sab."""
        upcoming_q = Q(
            status__in=ACTIVE_BOOKING_STATUSES,
            check_in__gte=timezone.localdate(),
        )
        return queryset.filter(upcoming_q) if value else queryset.exclude(upcoming_q)