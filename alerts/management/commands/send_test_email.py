from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError

PLACEHOLDERS = {"YOUR_GMAIL@gmail.com", "YOUR_APP_PASSWORD", "your@gmail.com", "your-16-char-app-password"}


class Command(BaseCommand):
    help = "Send a test email using the SMTP settings in .env"

    def add_arguments(self, parser):
        parser.add_argument(
            "recipient",
            nargs="?",
            default="",
            help="Email address to send the test to (defaults to EMAIL_HOST_USER)",
        )

    def handle(self, *args, **options):
        backend = settings.EMAIL_BACKEND
        if "console" in backend:
            raise CommandError(
                "EMAIL_BACKEND is still set to console. "
                "Set EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend in .env"
            )

        user = settings.EMAIL_HOST_USER
        password = settings.EMAIL_HOST_PASSWORD
        if not user or not password or user in PLACEHOLDERS or password in PLACEHOLDERS:
            raise CommandError(
                "Put your real Gmail address and App Password in .env "
                "(EMAIL_HOST_USER and EMAIL_HOST_PASSWORD), then retry."
            )

        recipient = options["recipient"] or user
        self.stdout.write(f"Sending test email to {recipient} via {settings.EMAIL_HOST}...")
        send_mail(
            subject="Domestic Gas Alarm — test email",
            message=(
                "If you received this, Gmail SMTP is configured correctly.\n\n"
                "Real refill alerts will go to each user's saved contact email."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        )
        self.stdout.write(self.style.SUCCESS(f"Test email sent to {recipient}"))
