from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.core.urls")),                
    path("api/auth/", include("apps.accounts.urls")),
    path("api/bookings/", include("apps.bookings.urls")),    
    path("api/payments/", include("apps.payments.urls")),  
    path("api/wishlist/", include("apps.wishlist.urls")),    
    path("api/", include("apps.reviews.urls")),         
    path("api/", include("apps.dashboard.urls")),
    path("api/", include("apps.properties.urls")),         
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)