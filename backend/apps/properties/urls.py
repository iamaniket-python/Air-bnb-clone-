from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import PropertyViewSet, AmenityViewSet

app_name = "properties"

router = DefaultRouter()

router.register(
    r"",
    PropertyViewSet,
    basename="property"
)

router.register(
    r"amenities",
    AmenityViewSet,
    basename="amenity"
)

urlpatterns = router.urls