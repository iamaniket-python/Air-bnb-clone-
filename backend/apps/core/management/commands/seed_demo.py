"""
Demo data for local development.

    python manage.py seed_demo              # users + properties + photos + bookings + reviews
    python manage.py seed_demo --no-images  # photos skip (Cloudinary quota bachane ke liye)

Idempotent: dobara chalane par duplicate nahi banta. Sirf DEBUG mein chalta hai (--force se override).
"""
import io
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.bookings.models import Booking
from apps.properties.models import Amenity, Property, PropertyImage
from apps.reviews.models import Review

PASSWORD = "StrongPass@123"  # sirf local demo ke liye

USERS = [
    # username, email, role, first_name, last_name
    ("admin_demo", "admin_demo@staynest.local", "admin", "Admin", "Demo"),
    ("host_asha", "host_asha@staynest.local", "host", "Asha", "Rao"),
    ("host_ravi", "host_ravi@staynest.local", "host", "Ravi", "Menon"),
    ("guest_meera", "guest_meera@staynest.local", "guest", "Meera", "Iyer"),
    ("guest_karan", "guest_karan@staynest.local", "guest", "Karan", "Shah"),
]

PROPERTIES = [
    {
        "host": "host_asha", "title": "Sea-facing apartment in Calangute",
        "description": "Bright 2BHK apartment, 5 minutes from the beach.\nBalcony with sea view, fast Wi-Fi and a fully equipped kitchen.",
        "property_type": "apartment", "address": "12 Beach Road", "city": "Goa", "state": "Goa",
        "postal_code": "403516", "latitude": "15.543900", "longitude": "73.755300",
        "price_per_night": "4500.00", "max_guests": 4, "bedrooms": 2, "beds": 2, "bathrooms": "2.0",
    },
    {
        "host": "host_asha", "title": "Heritage haveli near City Palace",
        "description": "A restored haveli with courtyard, rooftop dining and traditional Rajasthani decor.",
        "property_type": "house", "address": "7 Gangori Bazaar", "city": "Jaipur", "state": "Rajasthan",
        "postal_code": "302002", "latitude": "26.924000", "longitude": "75.826000",
        "price_per_night": "6500.00", "max_guests": 6, "bedrooms": 3, "beds": 4, "bathrooms": "3.0",
    },
    {
        "host": "host_asha", "title": "Cosy cottage in the Manali hills",
        "description": "Wooden cottage with pine forest view and a fireplace. Perfect for a winter getaway.",
        "property_type": "cottage", "address": "Old Manali Road", "city": "Manali", "state": "Himachal Pradesh",
        "postal_code": "175131", "latitude": "32.239600", "longitude": "77.188700",
        "price_per_night": "3200.00", "max_guests": 3, "bedrooms": 1, "beds": 2, "bathrooms": "1.0",
    },
    {
        "host": "host_ravi", "title": "Lake-view villa in Udaipur",
        "description": "Private villa overlooking Lake Pichola with pool, garden and a dedicated cook.",
        "property_type": "villa", "address": "Lake Pichola Road", "city": "Udaipur", "state": "Rajasthan",
        "postal_code": "313001", "latitude": "24.571300", "longitude": "73.691500",
        "price_per_night": "12000.00", "max_guests": 8, "bedrooms": 4, "beds": 5, "bathrooms": "4.0",
    },
    {
        "host": "host_ravi", "title": "Studio near Bandra station",
        "description": "Compact, modern studio in the heart of Bandra. Walk to cafes and the sea link.",
        "property_type": "apartment", "address": "Hill Road, Bandra West", "city": "Mumbai", "state": "Maharashtra",
        "postal_code": "400050", "latitude": "19.059600", "longitude": "72.829500",
        "price_per_night": "3800.00", "max_guests": 2, "bedrooms": 1, "beds": 1, "bathrooms": "1.0",
    },
    {
        "host": "host_ravi", "title": "Riverside guest house in Rishikesh",
        "description": "Peaceful guest house on the Ganges bank with yoga deck and sunrise views.",
        "property_type": "guest_house", "address": "Laxman Jhula Road", "city": "Rishikesh", "state": "Uttarakhand",
        "postal_code": "249302", "latitude": "30.126900", "longitude": "78.325900",
        "price_per_night": "2500.00", "max_guests": 4, "bedrooms": 2, "beds": 3, "bathrooms": "2.0",
    },
]

PALETTE = [(20, 120, 110), (180, 90, 60), (70, 100, 160), (120, 80, 150), (60, 130, 80), (170, 130, 40)]


def _field_names(model):
    return {f.name for f in model._meta.get_fields() if getattr(f, "concrete", False)}


def _create(model, **kwargs):
    """Sirf wahi kwargs bhejta hai jo model mein sach mein hain."""
    names = _field_names(model)
    return model.objects.create(**{k: v for k, v in kwargs.items() if k in names})


def _make_image(title, label, color):
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (1200, 800), color)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 680, 1200, 800], fill=(0, 0, 0))
    draw.text((40, 730), f"{title} - {label}", fill=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=80)
    return ContentFile(buf.getvalue())


class Command(BaseCommand):
    help = "Create demo users, properties, photos, bookings and reviews (DEBUG only)."

    def add_arguments(self, parser):
        parser.add_argument("--no-images", action="store_true", help="Skip generating/uploading photos.")
        parser.add_argument("--force", action="store_true", help="Run even when DEBUG is False.")

    def handle(self, *args, **options):
        if not settings.DEBUG and not options["force"]:
            raise CommandError("seed_demo only runs with DEBUG=True (use --force to override).")

        if not Amenity.objects.exists():
            call_command("seed_amenities", stdout=self.stdout)

        users = self._seed_users()
        props = self._seed_properties(users, with_images=not options["no_images"])
        self._seed_bookings(users, props)

        self.stdout.write(self.style.SUCCESS("\nDemo data ready. Login (password for all: %s):" % PASSWORD))
        for username, _email, role, *_ in USERS:
            self.stdout.write(f"  {role:<6} {username}")

    # ---------- users ----------
    def _seed_users(self):
        User = get_user_model()
        result = {}
        for username, email, role, first, last in USERS:
            user = User.objects.filter(username=username).first()
            if user is None:
                if role == "admin":
                    user = User.objects.create_superuser(username=username, email=email, password=PASSWORD)
                else:
                    user = User.objects.create_user(username=username, email=email, password=PASSWORD, role=role)
                user.first_name, user.last_name = first, last
                user.save()
                self.stdout.write(f"  + user {username}")
            result[username] = user
        return result

    # ---------- properties ----------
    def _seed_properties(self, users, with_images):
        amenities = list(Amenity.objects.order_by("id"))
        props = []
        for idx, data in enumerate(PROPERTIES):
            data = dict(data)
            host = users[data.pop("host")]
            title = data.pop("title")
            for key in ("latitude", "longitude", "price_per_night", "bathrooms"):
                data[key] = Decimal(data[key])
            prop, created = Property.objects.get_or_create(
                host=host, title=title, defaults={**data, "country": "India", "is_active": True}
            )
            if created:
                # har property ko amenities ka alag-alag slice
                prop.amenities.set(amenities[idx : idx + 8] or amenities)
                self.stdout.write(f"  + property {title}")
            if with_images and not prop.images.exists():
                color = PALETTE[idx % len(PALETTE)]
                for i, label in enumerate(("Living area", "Bedroom", "View")):
                    obj = PropertyImage(property=prop, caption=label, is_primary=(i == 0), display_order=i)
                    obj.image.save(f"demo-{prop.id}-{i}.jpg", _make_image(title, label, color), save=False)
                    obj.save()
            props.append(prop)
        return props

    # ---------- bookings + reviews ----------
    def _seed_bookings(self, users, props):
        today = timezone.localdate()
        meera, karan = users["guest_meera"], users["guest_karan"]

        # (property index, guest, start offset, nights, status, rating, comment)
        plan = [
            (0, meera, -30, 3, "completed", 5, "Amazing stay, spotless and right by the beach."),
            (1, meera, -30, 2, "completed", 4, "Beautiful haveli. Loved the rooftop dinner."),
            (3, meera, -30, 4, "completed", 5, "The villa and the cook were fantastic."),
            (0, karan, -20, 2, "completed", 4, "Great location, host was very helpful."),
            (2, karan, -20, 3, "completed", 5, "Cozy and peaceful. Will come back."),
            (4, karan, -20, 2, "completed", 3, "Good for a short stay, a bit small."),
            (1, karan, 10, 3, "pending", None, ""),
            (3, meera, 15, 3, "confirmed", None, ""),
        ]

        for idx, guest, offset, nights, status, rating, comment in plan:
            prop = props[idx]
            check_in = today + timedelta(days=offset)
            check_out = check_in + timedelta(days=nights)
            if Booking.objects.filter(property=prop, guest=guest, check_in=check_in).exists():
                continue
            try:
                with transaction.atomic():
                    booking = _create(
                        Booking,
                        property=prop, guest=guest, check_in=check_in, check_out=check_out,
                        num_guests=2, price_per_night=prop.price_per_night,
                        total_price=prop.price_per_night * nights, status=status,
                    )
                    if rating:
                        _create(
                            Review,
                            booking=booking, rating=rating, comment=comment,
                            property=prop, guest=guest, reviewer=guest, user=guest,
                        )
                self.stdout.write(f"  + booking #{booking.pk} ({status}) {prop.title}")
            except Exception as exc:  # noqa: BLE001 - seed command, crash nahi karna
                self.stderr.write(self.style.WARNING(f"  ! skipped booking for '{prop.title}': {exc}"))