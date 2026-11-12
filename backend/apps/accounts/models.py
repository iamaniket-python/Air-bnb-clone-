from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """
    Custom user model.
    Abhi minimal hai taaki migrations sahi order mein chalein.
    Phase 2 mein hum isme role (guest/host/admin), phone, etc. add karenge.
    """

    def __str__(self):
        return self.username