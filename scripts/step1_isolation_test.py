"""
Step 1: create two users with different data and verify isolation.
Run: python manage.py shell < scripts/step1_isolation_test.py
Or:  python scripts/step1_isolation_test.py  (via django setup below)
"""
import os
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import django

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth.models import User

from accounts.models import UserProfile
from alerts.models import Alert
from cylinders.models import Cylinder
from cylinders.services import calculate_gas_status, start_tracking

USERS = [
    {
        "username": "alice_gas",
        "password": "testpass123",
        "phone": "+91 9111111111",
        "alternate_phone": "+91 9222222222",
        "email": "alice@example.com",
        "start_date": date(2026, 8, 1),
        "initial_kg": Decimal("14.2"),
        "total_days": 30,
    },
    {
        "username": "bob_gas",
        "password": "testpass456",
        "phone": "+91 9333333333",
        "alternate_phone": "+91 9444444444",
        "email": "bob@example.com",
        "start_date": date(2026, 7, 1),
        "initial_kg": Decimal("5.0"),
        "total_days": 60,
    },
]


def setup_user(data):
    user, created = User.objects.get_or_create(username=data["username"])
    user.set_password(data["password"])
    user.save()

    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.phone = data["phone"]
    profile.alternate_phone = data["alternate_phone"]
    profile.email = data["email"]
    profile.save()

    user.cylinders.filter(is_active=True).update(is_active=False)
    start_tracking(user, data["start_date"], data["initial_kg"], data["total_days"])
    return user


def print_user_summary(label, user):
    profile = UserProfile.objects.get(user=user)
    cylinder = user.cylinders.filter(is_active=True).first()
    gas = calculate_gas_status(cylinder)
    alert_count = user.alerts.count()

    print(f"\n--- {label}: {user.username} ---")
    print(f"  Contacts: {profile.phone} | {profile.email}")
    print(f"  Cylinder: {gas.initial_kg} kg, {gas.total_days} days, started {gas.start_date}")
    print(f"  Live status: {gas.current_percent}% | {gas.current_kg} kg | {gas.days_left} days left")
    print(f"  Alerts in DB: {alert_count}")


def main():
    print("Setting up two isolated test accounts...")
    alice = setup_user(USERS[0])
    bob = setup_user(USERS[1])

    print_user_summary("User A", alice)
    print_user_summary("User B", bob)

    # Isolation checks
    alice_cylinders = Cylinder.objects.filter(user=alice).count()
    bob_cylinders = Cylinder.objects.filter(user=bob).count()
    alice_ids = set(alice.cylinders.values_list("id", flat=True))
    bob_ids = set(bob.cylinders.values_list("id", flat=True))
    shared_cylinders = bool(alice_ids & bob_ids)

    print("\n=== ISOLATION CHECKS ===")
    print(f"  Alice owns {alice_cylinders} cylinder row(s) — Bob owns {bob_cylinders}")
    print(f"  Shared cylinder rows between users? {shared_cylinders} (must be False)")

    alice_gas = calculate_gas_status(alice.cylinders.filter(is_active=True).first())
    bob_gas = calculate_gas_status(bob.cylinders.filter(is_active=True).first())
    data_differs = alice_gas.initial_kg != bob_gas.initial_kg and alice_gas.total_days != bob_gas.total_days
    print(f"  Alice and Bob have different gas data? {data_differs} (must be True)")

    if not shared_cylinders and data_differs:
        print("\nPASS: Users are isolated. Each account has its own cylinder and contacts.")
    else:
        print("\nFAIL: Isolation broken — investigate models/views.")

    print("\n--- Login credentials for browser test ---")
    print("  Alice: alice_gas / testpass123")
    print("  Bob:   bob_gas   / testpass456")
    print("  URL:   http://127.0.0.1:8000/login/")


if __name__ == "__main__":
    main()
