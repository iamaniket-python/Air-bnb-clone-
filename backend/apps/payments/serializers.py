from rest_framework import serializers

from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    """
    Safe output: provider_signature aur raw_response expose NAHI hote.
    """

    booking = serializers.IntegerField(source="booking_id", read_only=True)
    property_title = serializers.CharField(source="booking.property.title", read_only=True)
    guest_username = serializers.CharField(source="booking.guest.username", read_only=True)
    refund = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = [
            "transaction_id",
            "booking",
            "property_title",
            "guest_username",
            "amount",
            "currency",
            "provider",
            "status",
            "provider_order_id",
            "provider_payment_id",
            "failure_reason",
            "paid_at",
            "refund",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_refund(self, obj):
        return (obj.raw_response or {}).get("refund")


class PaymentCreateSerializer(serializers.Serializer):
    booking = serializers.IntegerField(min_value=1)


class PaymentVerifySerializer(serializers.Serializer):
    transaction_id = serializers.UUIDField()
    provider_payment_id = serializers.CharField(max_length=100)
    signature = serializers.CharField(max_length=256)


class MockCheckoutSerializer(serializers.Serializer):
    transaction_id = serializers.UUIDField()
    outcome = serializers.ChoiceField(choices=["success", "failure"], default="success")