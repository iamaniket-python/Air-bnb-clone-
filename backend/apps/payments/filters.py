import django_filters

from .models import Payment


class PaymentFilter(django_filters.FilterSet):
    booking = django_filters.NumberFilter(field_name="booking_id")
    status = django_filters.MultipleChoiceFilter(choices=Payment.Status.choices)
    provider = django_filters.ChoiceFilter(choices=Payment.Provider.choices)

    class Meta:
        model = Payment
        fields = []