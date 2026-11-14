from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.bookings.models import Booking
from apps.properties.models import Property

User = get_user_model()


class UpcomingReservationSerializer(serializers.ModelSerializer):
    property = serializers.SerializerMethodField()
    guest = serializers.CharField(source="guest.username", read_only=True)

    class Meta:
        model = Booking
        fields = [
            "id", "property", "guest", "check_in", "check_out",
            "num_guests", "total_price", "status",
        ]
        read_only_fields = fields

    def get_property(self, obj):
        return {"id": obj.property_id, "title": obj.property.title}


class AdminUserSerializer(serializers.ModelSerializer):
    # View queryset mein annotate hote hain (N+1 nahi)
    properties_count = serializers.IntegerField(read_only=True)
    bookings_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name", "role",
            "phone_number", "is_active", "date_joined", "last_login",
            "properties_count", "bookings_count",
        ]
        read_only_fields = fields


class AdminUserActiveSerializer(serializers.Serializer):
    """PATCH input. Instance = target user, context["request"] = admin."""

    is_active = serializers.BooleanField()

    def validate_is_active(self, value):
        user = self.instance
        request = self.context["request"]
        if value is False:
            if user.pk == request.user.pk:
                raise serializers.ValidationError(
                    "You cannot deactivate your own account."
                )
            if user.role == "admin" or user.is_superuser:
                raise serializers.ValidationError(
                    "Admin accounts cannot be deactivated here."
                )
        return value


class AdminHostSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name"]


class AdminPropertySerializer(serializers.ModelSerializer):
    host = AdminHostSerializer(read_only=True)
    bookings_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Property
        fields = [
            "id", "title", "property_type", "city", "state", "country",
            "price_per_night", "is_active", "average_rating", "review_count",
            "host", "bookings_count", "created_at", "updated_at",
        ]
        read_only_fields = fields


class AdminPropertyActiveSerializer(serializers.Serializer):
    is_active = serializers.BooleanField()