from django.contrib import admin
from django.urls import path

from accounts import views as account_views
from alerts import views as alert_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", account_views.home_view, name="home"),
    path("health/", account_views.health_view, name="health"),
    path("cron/check-alerts/", account_views.check_alerts_cron, name="check_alerts_cron"),
    path("login/", account_views.login_view, name="login"),
    path("register/", account_views.register_view, name="register"),
    path("logout/", account_views.logout_view, name="logout"),
    path("dashboard/", account_views.dashboard, name="dashboard"),
    path("start/", account_views.start_tracking_view, name="start"),
    path("contacts/", account_views.contacts_view, name="contacts"),
    path("alerts/", alert_views.alert_history, name="alerts"),
]
