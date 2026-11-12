import django_filters
from django import forms
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter

from apps.bookings.models import ACTIVE_BOOKING_STATUSES, Booking

from .models import Amenity, Property, PropertyAmenity

MAX_AMENITY_FILTERS = 10


class IntegerFilter(django_filters.NumberFilter):
    """Decimal ki jagah sirf poore numbers (guests=2.5 jaisa input reject)."""

    field_class = forms.IntegerField


class PropertyFilter(django_filters.FilterSet):
    destination = django_filters.CharFilter(method="filter_destination")
    check_in = django_filters.DateFilter(method="skip_filter")    # availability niche
    check_out = django_filters.DateFilter(method="skip_filter")   # filter_queryset mein lagti hai
    guests = IntegerFilter(field_name="max_guests", lookup_expr="gte", min_value=1)
    min_price = django_filters.NumberFilter(
        field_name="price_per_night", lookup_expr="gte", min_value=0
    )
    max_price = django_filters.NumberFilter(
        field_name="price_per_night", lookup_expr="lte", min_value=0
    )
    # distinct=False: iske bina django-filter poori query par DISTINCT laga deta hai
    property_type = django_filters.MultipleChoiceFilter(
        choices=Property.PropertyType.choices,
        distinct=False,
    )
    amenities = django_filters.ModelMultipleChoiceFilter(
        queryset=Amenity.objects.all(),
        method="filter_amenities",
    )
    min_rating = django_filters.NumberFilter(
        field_name="average_rating", lookup_expr="gte", min_value=0, max_value=5
    )

    class Meta:
        model = Property
        fields = []

    # -- individual filters -------------------------------------------------
    def skip_filter(self, queryset, name, value):
        return queryset

    def filter_destination(self, queryset, name, value):
        """'Calangute, Goa' -> har part city/state/country/address mein se kisi ek se match hona chahiye."""
        parts = [part.strip() for part in value.split(",") if part.strip()]
        for part in parts:
            queryset = queryset.filter(
                Q(city__icontains=part)
                | Q(state__icontains=part)
                | Q(country__icontains=part)
                | Q(address__icontains=part)
            )
        return queryset

    def filter_amenities(self, queryset, name, value):
        """Selected saari amenities honi chahiye (AND). JOIN ki jagah EXISTS: duplicate rows nahi."""
        amenity_ids = [amenity.pk for amenity in value]
        if len(amenity_ids) > MAX_AMENITY_FILTERS:
            raise ValidationError(
                {"amenities": f"You can filter by at most {MAX_AMENITY_FILTERS} amenities."}
            )
        for amenity_id in amenity_ids:
            queryset = queryset.filter(
                Exists(
                    PropertyAmenity.objects.filter(
                        property=OuterRef("pk"), amenity_id=amenity_id
                    )
                )
            )
        return queryset

    # -- cross-field validation + availability ------------------------------
    @staticmethod
    def _validate(data):
        errors = {}

        min_price, max_price = data.get("min_price"), data.get("max_price")
        if min_price is not None and max_price is not None and min_price > max_price:
            errors["min_price"] = "min_price cannot be greater than max_price."

        check_in, check_out = data.get("check_in"), data.get("check_out")
        if bool(check_in) != bool(check_out):
            missing = "check_out" if check_in else "check_in"
            errors[missing] = "Provide both check_in and check_out."
        elif check_in and check_out:
            if check_out <= check_in:
                errors["check_out"] = "check_out must be after check_in."
            if check_in < timezone.localdate():
                errors["check_in"] = "check_in cannot be in the past."

        if errors:
            raise ValidationError(errors)

    def filter_queryset(self, queryset):
        data = self.form.cleaned_data
        self._validate(data)

        queryset = super().filter_queryset(queryset)

        check_in, check_out = data.get("check_in"), data.get("check_out")
        if check_in and check_out:
            # Overlap: booking.check_in < search.check_out AND booking.check_out > search.check_in
            queryset = queryset.filter(
                ~Exists(
                    Booking.objects.filter(
                        property=OuterRef("pk"),
                        status__in=ACTIVE_BOOKING_STATUSES,
                        check_in__lt=check_out,
                        check_out__gt=check_in,
                    )
                )
            )
        return queryset


class StableOrderingFilter(OrderingFilter):
    """Har ordering ke end mein -id jodta hai, taaki tie hone par pagination stable rahe."""

    def get_ordering(self, request, queryset, view):
        ordering = super().get_ordering(request, queryset, view)
        if ordering:
            ordering = list(ordering)
            if "id" not in ordering and "-id" not in ordering:
                ordering.append("-id")
        return ordering