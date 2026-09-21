from django.core.management.base import BaseCommand

from alerts.services import process_user_alerts
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = "Check all active cylinders and send refill alerts when needed."

    def handle(self, *args, **options):
        sent = 0
        for user in User.objects.filter(is_active=True):
            alert = process_user_alerts(user)
            if alert:
                sent += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Alert sent for {user.username} ({alert.status})"
                    )
                )
        self.stdout.write(self.style.SUCCESS(f"Done. Alerts created: {sent}"))
