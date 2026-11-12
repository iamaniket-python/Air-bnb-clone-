from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "transaction_id",
        "booking",
        "amount",
        "currency",
        "provider",
        "status",
        "paid_at",
    )
    list_filter = ("status", "provider")
    search_fields = ("transaction_id", "provider_order_id", "provider_payment_id")
    readonly_fields = ("transaction_id", "raw_response")