from django.contrib import admin

from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("id", "booking", "rating", "created_at")
    list_filter = ("rating",)
    search_fields = ("booking__property__title", "booking__guest__username", "comment")
    list_select_related = ("booking__property", "booking__guest")