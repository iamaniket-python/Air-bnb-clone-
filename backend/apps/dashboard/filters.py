from django.contrib.auth import get_user_model
from django_filters import rest_framework as filters

from apps.properties.models import Property

User = get_user_model()


class AdminUserFilter(filters.FilterSet):
    role = filters.ChoiceFilter(choices=User.Role.choices)
    is_active = filters.BooleanFilter()

    class Meta:
        model = User
        fields = ["role", "is_active"]


class AdminPropertyFilter(filters.FilterSet):
    is_active = filters.BooleanFilter()
    property_type = filters.ChoiceFilter(choices=Property.PropertyType.choices)
    city = filters.CharFilter(field_name="city", lookup_expr="icontains")
    host = filters.NumberFilter(field_name="host_id")

    class Meta:
        model = Property
        fields = ["is_active", "property_type", "city", "host"]