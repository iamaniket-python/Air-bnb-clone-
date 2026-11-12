from django.contrib import admin

from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "property",
        "guest",
        "check_in",
        "check_out",
        "num_guests",
        "total_price",
        "status",
    )
    list_filter = ("status",)
    search_fields = ("property__title", "guest__username", "guest__email")
    list_select_related = ("property", "guest")
    date_hierarchy = "check_in"