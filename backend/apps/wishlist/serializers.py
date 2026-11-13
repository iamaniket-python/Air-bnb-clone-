from rest_framework import serializers

from apps.properties.models import Property

from .models import WishlistItem


class WishlistAddSerializer(serializers.Serializer):
    property = serializers.IntegerField(min_value=1)

    def validate_property(self, value):
        prop = Property.objects.filter(pk=value, is_active=True).first()
        if prop is None:
            raise serializers.ValidationError("Property not found or not available.")
        return prop  # validated_data["property"] ab Property instance hai


class WishlistPropertySerializer(serializers.ModelSerializer):
    """Property card. Images prefetched hain, to cover_image ke liye extra query nahi."""

    host = serializers.SerializerMethodField()
    cover_image = serializers.SerializerMethodField()

    class Meta:
        model = Property
        fields = [
            "id", "title", "property_type", "city", "state", "country",
            "price_per_night", "max_guests", "bedrooms", "beds", "bathrooms",
            "average_rating", "review_count", "cover_image", "host",
        ]
        read_only_fields = fields

    def get_host(self, obj):
        host = obj.host
        return {
            "id": host.id,
            "username": host.username,
            "first_name": host.first_name,
            "last_name": host.last_name,
        }

    def get_cover_image(self, obj):
        images = list(obj.images.all())  # prefetched, Meta ordering: primary pehle
        if not images or not images[0].image:
            return None
        url = images[0].image.url
        request = self.context.get("request")
        if request is not None and url.startswith("/"):
            return request.build_absolute_uri(url)
        return url


class WishlistItemSerializer(serializers.ModelSerializer):
    property = WishlistPropertySerializer(read_only=True)
    added_at = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = WishlistItem
        fields = ["id", "property", "added_at"]
        read_only_fields = fields