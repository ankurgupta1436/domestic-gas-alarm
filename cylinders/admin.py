from django.contrib import admin

from .models import Cylinder


@admin.register(Cylinder)
class CylinderAdmin(admin.ModelAdmin):
    list_display = ("user", "start_date", "initial_kg", "total_days", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("user__username",)
