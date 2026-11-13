from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.properties.models import Property

from . import services
from .models import Booking

User = get_user_model()


class UserSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name"]
        read_only_fields = fields


class PropertySummarySerializer(serializers.ModelSerializer):
    host = UserSummarySerializer(read_only=True)
    cover_image = serializers.SerializerMethodField()

    class Meta:
        model = Property
        fields = ["id", "title", "city", "state", "country", "property_type", "host", "cover_image"]
        read_only_fields = fields

    def get_cover_image(self, obj):
        # images prefetch hui hain; Meta ordering ki wajah se pehli image primary hoti hai
        images = list(obj.images.all())
        if not images or not images[0].image:
            return None
        url = images[0].image.url
        request = self.context.get("request")
        if request is not None and url.startswith("/"):
            return request.build_absolute_uri(url)
        return url


class BookingSerializer(serializers.ModelSerializer):
    property = PropertySummarySerializer(read_only=True)
    guest = UserSummarySerializer(read_only=True)
    nights = serializers.IntegerField(source="get_nights", read_only=True)
    available_actions = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            "id",
            "property",
            "guest",
            "check_in",
            "check_out",
            "nights",
            "num_guests",
            "price_per_night",
            "total_price",
            "status",
            "cancelled_at",
            "cancellation_reason",
            "available_actions",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_available_actions(self, obj):
        request = self.context.get("request")
        if request is None:
            return []
        return services.get_available_actions(obj, request.user)


class BookingCreateSerializer(serializers.Serializer):
    property = serializers.PrimaryKeyRelatedField(queryset=Property.objects.all())
    check_in = serializers.DateField()
    check_out = serializers.DateField()
    num_guests = serializers.IntegerField(min_value=1)

    def validate(self, attrs):
        if attrs["check_out"] <= attrs["check_in"]:
            raise serializers.ValidationError(
                {"check_out": "Check-out date must be after check-in date."}
            )
        return attrs


class BookingQuoteSerializer(serializers.Serializer):
    property = serializers.PrimaryKeyRelatedField(queryset=Property.objects.all())
    check_in = serializers.DateField()
    check_out = serializers.DateField()
    guests = serializers.IntegerField(min_value=1, default=1)

    def validate(self, attrs):
        if attrs["check_out"] <= attrs["check_in"]:
            raise serializers.ValidationError(
                {"check_out": "Check-out date must be after check-in date."}
            )
        return attrs


class BookingStatusSerializer(serializers.Serializer):
    STATUS_CHOICES = [
        (services.STATUS_CONFIRMED, "Confirmed"),
        (services.STATUS_REJECTED, "Rejected"),
        (services.STATUS_COMPLETED, "Completed"),
    ]
    status = serializers.ChoiceField(choices=STATUS_CHOICES)
    reason = serializers.CharField(required=False, allow_blank=True, max_length=500)


class BookingCancelSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, max_length=500)