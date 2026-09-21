from datetime import date
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from accounts.models import UserProfile
from alerts.services import process_user_alerts
from cylinders.services import calculate_gas_status, get_active_cylinder, start_tracking


def get_or_create_profile(user):
    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={"email": user.email},
    )
    return profile


@login_required
def dashboard(request):
    cylinder = get_active_cylinder(request.user)
    gas = calculate_gas_status(cylinder)
    profile = get_or_create_profile(request.user)
    process_user_alerts(request.user)

    return render(
        request,
        "dashboard.html",
        {
            "gas": gas,
            "profile": profile,
            "cylinder": cylinder,
        },
    )


@login_required
@require_POST
def start_tracking_view(request):
    start_date_raw = request.POST.get("start_date") or date.today().isoformat()
    try:
        start_date = date.fromisoformat(start_date_raw)
        initial_kg = Decimal(request.POST.get("initial_kg") or "14.2")
        total_days = int(request.POST.get("total_days") or "501")
    except (ValueError, InvalidOperation):
        messages.error(request, "Please enter valid tracking details.")
        return redirect("dashboard")

    if initial_kg <= 0 or total_days <= 0:
        messages.error(request, "Cylinder weight and total days must be greater than zero.")
        return redirect("dashboard")

    start_tracking(request.user, start_date, initial_kg, total_days)
    process_user_alerts(request.user)
    messages.success(request, "Gas usage tracking started.")
    return redirect("dashboard")


@login_required
def contacts_view(request):
    profile = get_or_create_profile(request.user)

    if request.method == "POST":
        profile.phone = request.POST.get("phone", "").strip()
        profile.alternate_phone = request.POST.get("alternate_phone", "").strip()
        profile.email = request.POST.get("email", "").strip()
        try:
            profile.alert_days_before = max(
                int(request.POST.get("alert_days_before") or profile.alert_days_before),
                0,
            )
        except ValueError:
            messages.error(request, "Alert days must be a whole number.")
            return redirect("contacts")
        profile.save(
            update_fields=[
                "phone",
                "alternate_phone",
                "email",
                "alert_days_before",
                "updated_at",
            ]
        )
        messages.success(request, "Contact details updated.")
        return redirect("contacts")

    return render(request, "contacts.html", {"profile": profile})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        messages.success(request, "Welcome back.")
        return redirect("dashboard")

    return render(request, "login.html", {"form": form})


def register_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    form = UserCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Account created. Save your alert contacts next.")
        return redirect("contacts")

    return render(request, "register.html", {"form": form})


def logout_view(request):
    logout(request)
    messages.info(request, "Logged out successfully.")
    return redirect("login")


def home_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return redirect("login")


@require_GET
def health_view(request):
    return JsonResponse({"status": "ok"})


@csrf_exempt
def check_alerts_cron(request):
    """Free-tier scheduled alerts: ping this URL from cron-job.org."""
    expected = settings.CRON_SECRET
    provided = request.headers.get("X-Cron-Secret") or request.GET.get("secret", "")
    if not expected or provided != expected:
        return HttpResponseForbidden("Invalid or missing cron secret.")

    created = 0
    for user in User.objects.filter(is_active=True):
        if process_user_alerts(user):
            created += 1
    return HttpResponse(f"Alerts created: {created}")
