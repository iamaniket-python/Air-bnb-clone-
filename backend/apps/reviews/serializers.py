from rest_framework import serializers

from .models import Review


class ReviewCreateSerializer(serializers.Serializer):
    """Sirf input validation. Business rules services.py mein hain."""

    booking = serializers.IntegerField(min_value=1)
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(max_length=2000, trim_whitespace=True)


class ReviewSerializer(serializers.ModelSerializer):
    booking = serializers.IntegerField(source="booking_id", read_only=True)
    property = serializers.SerializerMethodField()
    reviewer = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ["id", "booking", "property", "reviewer", "rating", "comment", "created_at"]
        read_only_fields = fields

    def get_property(self, obj):
        prop = obj.booking.property
        return {"id": prop.id, "title": prop.title, "city": prop.city}

    def get_reviewer(self, obj):
        guest = obj.booking.guest
        full_name = f"{guest.first_name} {guest.last_name}".strip()
        return {
            "id": guest.id,
            "username": guest.username,
            "first_name": guest.first_name,
            "last_name": guest.last_name,
            "display_name": full_name or guest.username,
        }