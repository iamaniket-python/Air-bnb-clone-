from django.db import transaction
from rest_framework import serializers

from apps.accounts.models import User

from .models import Amenity, Property, PropertyImage

MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB per image


# ---------------------------------------------------------------------------
# Amenity
# ---------------------------------------------------------------------------
class AmenitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Amenity
        fields = ("id", "name", "icon")


# ---------------------------------------------------------------------------
# Images
# ---------------------------------------------------------------------------
class PropertyImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyImage
        fields = ("id", "image", "caption", "is_primary", "display_order")
        read_only_fields = fields


class PropertyImageUploadSerializer(serializers.Serializer):
    images = serializers.ListField(
        child=serializers.ImageField(),
        allow_empty=False,
        max_length=10,  # ek request mein max 10
    )

    def validate_images(self, files):
        for file in files:
            if file.size > MAX_IMAGE_SIZE:
                raise serializers.ValidationError(f"{file.name} is larger than 5 MB.")
        return files


class PropertyImageUpdateSerializer(serializers.Serializer):
    caption = serializers.CharField(required=False, allow_blank=True, max_length=200)
    display_order = serializers.IntegerField(required=False, min_value=0)
    is_primary = serializers.BooleanField(required=False)


# ---------------------------------------------------------------------------
# Host info (public detail page par)
# ---------------------------------------------------------------------------
class HostSummarySerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    profile_picture = serializers.ImageField(source="profile.profile_picture", read_only=True)

    class Meta:
        model = User
        fields = ("id", "full_name", "profile_picture", "date_joined")

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


# ---------------------------------------------------------------------------
# Property: list / detail / write
# ---------------------------------------------------------------------------
class PropertyListSerializer(serializers.ModelSerializer):
    """Cards ke liye halka serializer."""

    primary_image = serializers.SerializerMethodField()
    host_name = serializers.SerializerMethodField()

    class Meta:
        model = Property
        fields = (
            "id",
            "title",
            "property_type",
            "city",
            "state",
            "country",
            "price_per_night",
            "max_guests",
            "bedrooms",
            "beds",
            "bathrooms",
            "average_rating",
            "review_count",
            "is_active",
            "primary_image",
            "host_name",
            "created_at",
        )
        read_only_fields = fields

    def get_primary_image(self, obj):
        # prefetch ki hui images use hoti hain (extra query nahi); Meta ordering ki wajah se
        # primary image sabse pehle aati hai
        images = list(obj.images.all())
        if not images:
            return None
        url = images[0].image.url
        request = self.context.get("request")
        return request.build_absolute_uri(url) if request else url

    def get_host_name(self, obj):
        return obj.host.get_full_name() or obj.host.username


class PropertyDetailSerializer(serializers.ModelSerializer):
    host = HostSummarySerializer(read_only=True)
    images = PropertyImageSerializer(many=True, read_only=True)
    amenities = AmenitySerializer(many=True, read_only=True)

    class Meta:
        model = Property
        fields = (
            "id",
            "title",
            "description",
            "property_type",
            "address",
            "city",
            "state",
            "country",
            "postal_code",
            "latitude",
            "longitude",
            "price_per_night",
            "max_guests",
            "bedrooms",
            "beds",
            "bathrooms",
            "is_active",
            "average_rating",
            "review_count",
            "host",
            "images",
            "amenities",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class PropertyWriteSerializer(serializers.ModelSerializer):
    """Create/update validation. Response detail serializer ke format mein aata hai."""

    amenity_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Amenity.objects.all(),
        write_only=True,
        required=False,
    )

    class Meta:
        model = Property
        fields = (
            "title",
            "description",
            "property_type",
            "address",
            "city",
            "state",
            "country",
            "postal_code",
            "latitude",
            "longitude",
            "price_per_night",
            "max_guests",
            "bedrooms",
            "beds",
            "bathrooms",
            "is_active",
            "amenity_ids",
        )
        extra_kwargs = {
            "title": {"min_length": 5},
            "description": {"min_length": 20},
            "max_guests": {"min_value": 1, "max_value": 50},
            "bedrooms": {"min_value": 0, "max_value": 50},
            "beds": {"min_value": 1, "max_value": 100},
            "bathrooms": {"min_value": 1, "max_value": 50},
        }

    def validate(self, attrs):
        # Partial update mein purani value bhi dekhni padti hai
        latitude = attrs.get("latitude", getattr(self.instance, "latitude", None))
        longitude = attrs.get("longitude", getattr(self.instance, "longitude", None))

        if (latitude is None) != (longitude is None):
            raise serializers.ValidationError(
                {"latitude": "Latitude and longitude must be provided together."}
            )
        if latitude is not None and not (-90 <= latitude <= 90):
            raise serializers.ValidationError({"latitude": "Latitude must be between -90 and 90."})
        if longitude is not None and not (-180 <= longitude <= 180):
            raise serializers.ValidationError(
                {"longitude": "Longitude must be between -180 and 180."}
            )
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        amenities = validated_data.pop("amenity_ids", None)
        instance = super().create(validated_data)  # host view se (perform_create) aata hai
        if amenities:
            instance.amenities.set(amenities)
        return instance

    @transaction.atomic
    def update(self, instance, validated_data):
        amenities = validated_data.pop("amenity_ids", None)
        instance = super().update(instance, validated_data)
        if amenities is not None:
            instance.amenities.set(amenities)
        return instance

    def to_representation(self, instance):
        return PropertyDetailSerializer(instance, context=self.context).data