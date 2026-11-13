from rest_framework import mixins, viewsets
from rest_framework import status as http_status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.pagination import StandardPagination
from apps.core.permissions import IsGuest

from . import gateways, services
from .filters import PaymentFilter
from .models import Payment
from .serializers import (
    MockCheckoutSerializer,
    PaymentCreateSerializer,
    PaymentSerializer,
    PaymentVerifySerializer,
)


class PaymentViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = PaymentSerializer
    pagination_class = StandardPagination
    filterset_class = PaymentFilter
    ordering_fields = ["created_at", "amount", "paid_at"]
    ordering = ["-created_at", "-id"]
    lookup_field = "transaction_id"
    lookup_value_regex = r"[0-9a-fA-F-]{36}"

    def get_permissions(self):
        if self.action in ("create_payment", "verify", "mock_checkout"):
            return [IsAuthenticated(), IsGuest()]
        return [IsAuthenticated()]

    def get_queryset(self):
        queryset = Payment.objects.select_related(
            "booking", "booking__property", "booking__guest"
        )
        user = self.request.user
        if user.is_platform_admin:
            return queryset
        if user.is_host:
            return queryset.filter(booking__property__host=user)
        return queryset.filter(booking__guest=user)

    def _serialize(self, payment):
        payment = self.get_queryset().get(pk=payment.pk)
        return PaymentSerializer(payment, context=self.get_serializer_context()).data

    @action(detail=False, methods=["post"], url_path="create", url_name="create")
    def create_payment(self, request):
        serializer = PaymentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payment, created = services.create_payment(
            booking_id=serializer.validated_data["booking"],
            user=request.user,
        )
        return Response(
            {
                "payment": self._serialize(payment),
                "checkout": services.get_checkout_payload(payment),
            },
            status=http_status.HTTP_201_CREATED if created else http_status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"], url_path="verify", url_name="verify")
    def verify(self, request):
        serializer = PaymentVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        payment, newly_verified = services.verify_payment(
            transaction_id=data["transaction_id"],
            user=request.user,
            provider_payment_id=data["provider_payment_id"],
            signature=data["signature"],
        )
        message = (
            "Payment verified successfully."
            if newly_verified
            else "Payment was already verified."
        )
        return Response({"message": message, "payment": self._serialize(payment)})

    @action(detail=False, methods=["post"], url_path="mock-checkout", url_name="mock-checkout")
    def mock_checkout(self, request):
        # Production mein ye endpoint exist hi nahi karta (404)
        if not gateways.is_mock_enabled():
            raise NotFound()

        serializer = MockCheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        result = services.simulate_mock_checkout(
            transaction_id=data["transaction_id"],
            user=request.user,
            outcome=data["outcome"],
        )
        return Response(result)