from django.contrib import admin

from .models import Alert


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at", "status", "email_status", "sms_status", "reason_key")
    list_filter = ("status", "email_status", "sms_status")
    search_fields = ("user__username", "message", "email", "phone")
