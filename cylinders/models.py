from django.conf import settings
from django.db import models


class Cylinder(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cylinders",
    )
    start_date = models.DateField()
    initial_kg = models.DecimalField(max_digits=6, decimal_places=2, default=14.2)
    total_days = models.PositiveIntegerField(default=501)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.user.username} cylinder from {self.start_date}"
