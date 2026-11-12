from django.db import connection
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def health_check(request):
    """
    Server aur database ka status check karta hai.
    Deployment (load balancer / uptime monitor) mein bhi kaam aata hai.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        db_status = "connected"
        http_status = status.HTTP_200_OK
    except Exception:
        db_status = "unavailable"
        http_status = status.HTTP_503_SERVICE_UNAVAILABLE

    return Response(
        {
            "status": "ok" if db_status == "connected" else "error",
            "database": db_status,
        },
        status=http_status,
    )