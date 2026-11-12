import logging

from rest_framework import generics, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import User
from .serializers import (
    ChangePasswordSerializer,
    ForgotPasswordSerializer,
    LoginSerializer,
    LogoutSerializer,
    ProfileSerializer,
    RegisterSerializer,
    ResetPasswordSerializer,
    UserSummarySerializer,
)
from .services import get_tokens_for_user, send_password_reset_email

logger = logging.getLogger(__name__)


class RegisterView(generics.CreateAPIView):
    """POST /api/auth/register/"""

    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    authentication_classes = []  # public endpoint: kharab/expired token header se 401 na aaye
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                "user": UserSummarySerializer(user).data,
                "tokens": get_tokens_for_user(user),
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(TokenObtainPairView):
    """POST /api/auth/login/  (username ya email + password)"""

    serializer_class = LoginSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"


class LogoutView(APIView):
    """POST /api/auth/logout/  body: {"refresh": "<token>"}"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "Logged out successfully."})


class ProfileView(generics.RetrieveUpdateAPIView):
    """GET / PUT / PATCH /api/auth/profile/"""

    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]  # picture upload ke liye

    def get_object(self):
        return User.objects.select_related("profile").get(pk=self.request.user.pk)


class ForgotPasswordView(APIView):
    """POST /api/auth/password/forgot/  body: {"email": "..."}"""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password_reset"

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user:
            try:
                send_password_reset_email(user)
            except Exception:
                # Email fail ho to bhi same response (user enumeration se bachav)
                logger.exception("Password reset email failed for user id=%s", user.pk)

        return Response(
            {"message": "If an account exists with this email, a password reset link has been sent."}
        )


class ResetPasswordView(APIView):
    """POST /api/auth/password/reset/"""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password_reset"

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "Password has been reset successfully. Please login."})


class ChangePasswordView(APIView):
    """POST /api/auth/password/change/"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "Password changed successfully. Please login again."})