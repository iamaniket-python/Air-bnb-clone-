from rest_framework import serializers

from apps.accounts.models import User
from apps.properties.models import Property

from .services import ASSIGNABLE_ROLES


class AdminUserSerializer(serializers.ModelSerializer):
    # Queryset annotations (views.py mein annotate hota hai)
    property_count = serializers.IntegerField(read_only=True)
    booking_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name", "role",
            "phone_number", "is_active", "date_joined", "property_count", "booking_count",
        ]
        read_only_fields = fields


class AdminUserUpdateSerializer(serializers.Serializer):
    is_active = serializers.BooleanField(required=False)
    role = serializers.ChoiceField(choices=ASSIGNABLE_ROLES, required=False)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("Provide 'is_active' and/or 'role'.")
        return attrs


class AdminPropertySerializer(serializers.ModelSerializer):
    host = serializers.SerializerMethodField()

    class Meta:
        model = Property
        fields = [
            "id", "title", "property_type", "city", "state", "country",
            "price_per_night", "is_active", "average_rating", "review_count",
            "host", "created_at",
        ]
        read_only_fields = fields

    def get_host(self, obj):
        return {"id": obj.host.id, "username": obj.host.username}


class AdminPropertyUpdateSerializer(serializers.Serializer):
    is_active = serializers.BooleanField()