from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import UserProfile
from alerts.models import Alert
from alerts.services import process_user_alerts
from cylinders.services import calculate_gas_status, start_tracking


class IsolationAndAlertsTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user("alice_gas", password="testpass123")
        self.bob = User.objects.create_user("bob_gas", password="testpass456")
        alice_profile = UserProfile.objects.get(user=self.alice)
        alice_profile.email = "alice@example.com"
        alice_profile.phone = "+91 9111111111"
        alice_profile.save()
        bob_profile = UserProfile.objects.get(user=self.bob)
        bob_profile.email = "bob@example.com"
        bob_profile.phone = "+91 9333333333"
        bob_profile.save()

        start_tracking(self.alice, date.today() - timedelta(days=4), Decimal("14.2"), 30)
        start_tracking(self.bob, date.today(), Decimal("5.0"), 60)

    def test_each_user_sees_only_their_cylinder(self):
        self.client.login(username="alice_gas", password="testpass123")
        alice_page = self.client.get(reverse("dashboard"))
        self.assertContains(alice_page, "14.20")
        self.assertNotContains(alice_page, "9333333333")

        self.client.logout()
        self.client.login(username="bob_gas", password="testpass456")
        bob_page = self.client.get(reverse("dashboard"))
        self.assertContains(bob_page, "5.00")
        self.assertNotContains(bob_page, "9111111111")

    def test_contacts_are_saved_per_user(self):
        self.client.login(username="alice_gas", password="testpass123")
        self.client.post(
            reverse("contacts"),
            {
                "phone": "+91 9000000001",
                "alternate_phone": "+91 9000000002",
                "email": "alice-alerts@example.com",
                "alert_days_before": "5",
            },
        )
        profile = UserProfile.objects.get(user=self.alice)
        self.assertEqual(profile.email, "alice-alerts@example.com")
        self.assertEqual(profile.alert_days_before, 5)
        self.assertEqual(UserProfile.objects.get(user=self.bob).email, "bob@example.com")

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_alert_email_goes_to_that_users_contact(self):
        start_tracking(self.alice, date.today() - timedelta(days=28), Decimal("14.2"), 30)
        alert = process_user_alerts(self.alice)
        self.assertIsNotNone(alert)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["alice@example.com"])
        self.assertFalse(Alert.objects.filter(user=self.bob).exists())

    def test_gas_math_on_day_one(self):
        cylinder = start_tracking(self.bob, date.today(), Decimal("10.00"), 10)
        gas = calculate_gas_status(cylinder)
        self.assertEqual(gas.current_percent, Decimal("100.00"))
        self.assertEqual(gas.days_left, 9)

    def test_health_endpoint(self):
        response = self.client.get(reverse("health"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
