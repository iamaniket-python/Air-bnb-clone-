from django.urls import path

from .views import (
    MyReviewListView,
    PropertyReviewListView,
    ReviewDeleteView,
    ReviewListCreateView,
)

app_name = "reviews"

# Ye urls config/urls.py mein "api/" ke neeche, properties include se PEHLE aate hain
urlpatterns = [
    path("reviews/", ReviewListCreateView.as_view(), name="review-list-create"),
    path("reviews/my/", MyReviewListView.as_view(), name="review-my"),
    path("reviews/<int:pk>/", ReviewDeleteView.as_view(), name="review-delete"),
    path(
        "properties/<int:property_id>/reviews/",
        PropertyReviewListView.as_view(),
        name="property-reviews",
    ),
]