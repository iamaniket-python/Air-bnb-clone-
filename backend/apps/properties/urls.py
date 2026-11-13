from rest_framework.routers import SimpleRouter

from .views import AmenityViewSet, PropertyViewSet

app_name = "properties"

router = SimpleRouter()
router.register("properties", PropertyViewSet, basename="property")
router.register("amenities", AmenityViewSet, basename="amenity")

urlpatterns = router.urls