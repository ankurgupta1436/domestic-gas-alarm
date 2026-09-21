from django.contrib import admin

from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone", "email", "alert_days_before", "updated_at")
    search_fields = ("user__username", "phone", "email")
