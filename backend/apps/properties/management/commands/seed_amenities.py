from django.core.management.base import BaseCommand

from apps.properties.models import Amenity

# (name, react-icons ka icon naam)
AMENITIES = [
    ("Wi-Fi", "FaWifi"),
    ("Air Conditioning", "FaSnowflake"),
    ("Swimming Pool", "FaSwimmingPool"),
    ("Free Parking", "FaParking"),
    ("Television", "FaTv"),
    ("Kitchen", "FaUtensils"),
    ("Washing Machine", "MdLocalLaundryService"),
    ("Heating", "FaFire"),
    ("Gym", "FaDumbbell"),
    ("Hot Tub", "FaHotTub"),
    ("Pet Friendly", "FaPaw"),
    ("Balcony", "MdBalcony"),
    ("Power Backup", "FaBolt"),
    ("Breakfast Included", "FaCoffee"),
    ("First Aid Kit", "FaFirstAid"),
    ("Security Cameras", "FaVideo"),
]


class Command(BaseCommand):
    help = "Default amenities add karta hai (dobara chalane par duplicate nahi banata)."

    def handle(self, *args, **options):
        created_count = 0
        for name, icon in AMENITIES:
            _, created = Amenity.objects.get_or_create(name=name, defaults={"icon": icon})
            created_count += int(created)

        self.stdout.write(
            self.style.SUCCESS(
                f"{created_count} new amenities added, "
                f"{len(AMENITIES) - created_count} already existed."
            )
        )