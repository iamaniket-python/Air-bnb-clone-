from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import RegexValidator
from django.utils import timezone
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User
from .services import blacklist_all_tokens

PHONE_VALIDATOR = RegexValidator(
    regex=r"^\+?[0-9]{10,14}$",
    message="Enter a valid phone number (10-14 digits, optional leading +).",
)

MAX_PROFILE_PICTURE_SIZE = 2 * 1024 * 1024  # 2 MB


# def run_password_validators(password, user):
#     """Django ke password validators chalao aur DRF-style error raise karo."""
#     try:
#         validate_password(password, user=user)
#     except DjangoValidationError as exc:
#         raise serializers.ValidationError(list(exc.messages))


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
class UserSummarySerializer(serializers.ModelSerializer):
    """Login/register response mein chhota user object."""

    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name", "role")
        read_only_fields = fields


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    password2 = serializers.CharField(write_only=True, style={"input_type": "password"})
    # Admin role register se nahi mil sakta
    role = serializers.ChoiceField(
        choices=[(User.Role.GUEST, "Guest"), (User.Role.HOST, "Host")],
        default=User.Role.GUEST,
    )
    phone_number = serializers.CharField(
        required=False,
        allow_blank=True,
        validators=[PHONE_VALIDATOR],
    )

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "role",
            "password",
            "password2",
        )
        extra_kwargs = {"first_name": {"required": True, "allow_blank": False}}

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password2": "Passwords do not match."})

        candidate = User(
            username=attrs.get("username"),
            email=attrs.get("email"),
            first_name=attrs.get("first_name", ""),
            last_name=attrs.get("last_name", ""),
        )
        try:
            validate_password(attrs["password"], user=candidate)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)})
        return attrs

    def create(self, validated_data):
        validated_data.pop("password2")
        password = validated_data.pop("password")
        return User.objects.create_user(password=password, **validated_data)


class LoginSerializer(TokenObtainPairSerializer):
    """
    'username' field mein username YA email dono chalenge.
    Token mein role aur username claims add hote hain.
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        token["username"] = user.username
        return token

    def validate(self, attrs):
        identifier = (attrs.get(self.username_field) or "").strip()
        if "@" in identifier:
            user = User.objects.filter(email__iexact=identifier).first()
            if user:
                attrs[self.username_field] = user.get_username()

        data = super().validate(attrs)
        data["user"] = UserSummarySerializer(self.user).data
        return data


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def validate(self, attrs):
        try:
            self.token = RefreshToken(attrs["refresh"])
        except TokenError:
            raise serializers.ValidationError({"refresh": "Invalid or expired token."})

        # Doosre user ka token blacklist na kar sake
        if str(self.token.get("user_id")) != str(self.context["request"].user.pk):
            raise serializers.ValidationError({"refresh": "This token does not belong to you."})
        return attrs

    def save(self, **kwargs):
        try:
            self.token.blacklist()
        except TokenError:
            pass


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------
class ProfileSerializer(serializers.ModelSerializer):
    """
    User + UserProfile ek flat object mein (multipart upload ke liye flat hi chahiye).
    Read-only: id, username, email, role, date_joined.
    """

    phone_number = serializers.CharField(
        required=False,
        allow_blank=True,
        validators=[PHONE_VALIDATOR],
    )
    profile_picture = serializers.ImageField(source="profile.profile_picture", required=False)
    bio = serializers.CharField(source="profile.bio", required=False, allow_blank=True)
    date_of_birth = serializers.DateField(
        source="profile.date_of_birth", required=False, allow_null=True
    )
    city = serializers.CharField(source="profile.city", required=False, allow_blank=True)
    state = serializers.CharField(source="profile.state", required=False, allow_blank=True)
    country = serializers.CharField(source="profile.country", required=False, allow_blank=True)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "role",
            "first_name",
            "last_name",
            "phone_number",
            "bio",
            "date_of_birth",
            "city",
            "state",
            "country",
            "profile_picture",
            "date_joined",
        )
        read_only_fields = ("id", "username", "email", "role", "date_joined")

    def validate_profile_picture(self, value):
        if value and value.size > MAX_PROFILE_PICTURE_SIZE:
            raise serializers.ValidationError("Image size must be 2 MB or less.")
        return value

    def validate_date_of_birth(self, value):
        if value and value >= timezone.localdate():
            raise serializers.ValidationError("Date of birth must be in the past.")
        return value

    def update(self, instance, validated_data):
        profile_data = validated_data.pop("profile", {})

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        profile = instance.profile
        for attr, value in profile_data.items():
            setattr(profile, attr, value)
        profile.save()

        return instance


# ---------------------------------------------------------------------------
# Passwords
# ---------------------------------------------------------------------------
class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, style={"input_type": "password"})
    new_password2 = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate(self, attrs):
        try:
            user_id = force_str(urlsafe_base64_decode(attrs["uid"]))
            user = User.objects.get(pk=user_id, is_active=True)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError({"token": "Invalid or expired reset link."})

        if not default_token_generator.check_token(user, attrs["token"]):
            raise serializers.ValidationError({"token": "Invalid or expired reset link."})

        if attrs["new_password"] != attrs["new_password2"]:
            raise serializers.ValidationError({"new_password2": "Passwords do not match."})

        try:
            validate_password(attrs["new_password"], user=user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"new_password": list(exc.messages)})

        attrs["user"] = user
        return attrs

    def save(self, **kwargs):
        user = self.validated_data["user"]
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        blacklist_all_tokens(user)
        return user


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True, style={"input_type": "password"})
    new_password = serializers.CharField(write_only=True, style={"input_type": "password"})
    new_password2 = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate_old_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value

    def validate(self, attrs):
        user = self.context["request"].user

        if attrs["new_password"] != attrs["new_password2"]:
            raise serializers.ValidationError({"new_password2": "Passwords do not match."})
        if attrs["new_password"] == attrs["old_password"]:
            raise serializers.ValidationError(
                {"new_password": "New password must be different from the old one."}
            )

        try:
            validate_password(attrs["new_password"], user=user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"new_password": list(exc.messages)})
        return attrs

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        blacklist_all_tokens(user)
        return user