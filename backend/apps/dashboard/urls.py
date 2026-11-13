from django.urls import path

from .views import (
    AdminDashboardView,
    AdminPropertyDetailView,
    AdminPropertyListView,
    AdminUserDetailView,
    AdminUserListView,
    HostDashboardView,
)

app_name = "dashboard"

# config/urls.py mein "api/" ke neeche include hota hai
urlpatterns = [
    path("host/dashboard/", HostDashboardView.as_view(), name="host-dashboard"),
    path("admin/dashboard/", AdminDashboardView.as_view(), name="admin-dashboard"),
    path("admin/users/", AdminUserListView.as_view(), name="admin-user-list"),
    path("admin/users/<int:pk>/", AdminUserDetailView.as_view(), name="admin-user-detail"),
    path("admin/properties/", AdminPropertyListView.as_view(), name="admin-property-list"),
    path(
        "admin/properties/<int:pk>/",
        AdminPropertyDetailView.as_view(),
        name="admin-property-detail",
    ),
]