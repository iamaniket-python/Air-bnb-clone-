from django.urls import path

from .views import HostDashboardView

app_name = "host"

urlpatterns = [
    path("dashboard/", HostDashboardView.as_view(), name="dashboard"),
]