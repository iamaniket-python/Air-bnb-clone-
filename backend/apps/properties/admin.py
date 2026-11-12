from django.contrib import admin

from .models import Amenity, Property, PropertyAmenity, PropertyImage


class PropertyImageInline(admin.TabularInline):
    model = PropertyImage
    extra = 1


class PropertyAmenityInline(admin.TabularInline):
    model = PropertyAmenity
    extra = 1


@admin.register(Amenity)
class AmenityAdmin(admin.ModelAdmin):
    list_display = ("name", "icon")
    search_fields = ("name",)


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "host",
        "city",
        "property_type",
        "price_per_night",
        "average_rating",
        "is_active",
    )
    list_filter = ("property_type", "is_active", "country")
    search_fields = ("title", "city", "host__username")
    list_select_related = ("host",)
    readonly_fields = ("average_rating", "review_count")
    inlines = [PropertyImageInline, PropertyAmenityInline]