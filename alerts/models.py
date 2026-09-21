from django.conf import settings
from django.db import models


class AlertDeliveryStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    SENT = "sent", "Sent"
    PARTIAL = "partial", "Partially sent"
    FAILED = "failed", "Failed"
    SKIPPED = "skipped", "Skipped"


class Alert(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="alerts",
    )
    cylinder = models.ForeignKey(
        "cylinders.Cylinder",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alerts",
    )
    reason_key = models.CharField(max_length=64, db_index=True)
    message = models.TextField()
    channels = models.CharField(max_length=120, default="Email, SMS")
    phone = models.CharField(max_length=20, blank=True, default="")
    alternate_phone = models.CharField(max_length=20, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    email_status = models.CharField(
        max_length=20,
        choices=AlertDeliveryStatus.choices,
        default=AlertDeliveryStatus.PENDING,
    )
    sms_status = models.CharField(
        max_length=20,
        choices=AlertDeliveryStatus.choices,
        default=AlertDeliveryStatus.PENDING,
    )
    status = models.CharField(
        max_length=20,
        choices=AlertDeliveryStatus.choices,
        default=AlertDeliveryStatus.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "reason_key"],
                name="unique_alert_per_user_reason",
            )
        ]

    def __str__(self) -> str:
        return f"Alert for {self.user.username} ({self.reason_key})"
