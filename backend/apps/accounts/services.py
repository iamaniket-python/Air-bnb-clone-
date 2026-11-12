"""
Accounts ka business logic. Views patle rehte hain, logic yahan rehta hai.
"""
import logging

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

logger = logging.getLogger(__name__)


def get_tokens_for_user(user):
    """Register ke baad direct login ke liye access + refresh tokens."""
    refresh = RefreshToken.for_user(user)
    refresh["role"] = user.role
    refresh["username"] = user.username
    return {"refresh": str(refresh), "access": str(refresh.access_token)}


def blacklist_all_tokens(user):
    """User ke saare refresh tokens invalid (password change/reset ke baad)."""
    for token in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=token)


def send_password_reset_email(user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    reset_link = f"{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}"

    message = (
        f"Hi {user.first_name or user.username},\n\n"
        "We received a request to reset your StayNest password.\n"
        f"Click the link below to choose a new password:\n\n{reset_link}\n\n"
        "This link is valid for 1 hour and can be used only once.\n"
        "If you did not request this, you can safely ignore this email.\n"
    )
    send_mail(
        subject="Reset your StayNest password",
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )