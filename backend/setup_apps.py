"""
One-time script: apps/ package ke andar saare Django apps banata hai
aur unka apps.py sahi 'apps.<name>' ke saath likhta hai.
Run: python setup_apps.py
"""
import subprocess
import sys
from pathlib import Path

APPS = [
    "core",
    "accounts",
    "properties",
    "bookings",
    "payments",
    "reviews",
    "wishlist",
    "dashboard",
]

base = Path("apps")
base.mkdir(exist_ok=True)
(base / "__init__.py").touch()

for name in APPS:
    app_path = base / name
    app_path.mkdir(exist_ok=True)

    if not (app_path / "apps.py").exists():
        subprocess.run(
            [sys.executable, "manage.py", "startapp", name, str(app_path)],
            check=True,
        )

    class_name = "".join(part.capitalize() for part in name.split("_")) + "Config"
    (app_path / "apps.py").write_text(
        "from django.apps import AppConfig\n\n\n"
        f"class {class_name}(AppConfig):\n"
        '    default_auto_field = "django.db.models.BigAutoField"\n'
        f'    name = "apps.{name}"\n',
        encoding="utf-8",
    )
    print(f"Created app: apps/{name}")

Path("media").mkdir(exist_ok=True)
print("Done.")