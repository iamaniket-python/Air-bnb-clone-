from rest_framework.routers import SimpleRouter

from .views import BookingViewSet

app_name = "bookings"

router = SimpleRouter()
router.register("", BookingViewSet, basename="booking")

urlpatterns = router.urls