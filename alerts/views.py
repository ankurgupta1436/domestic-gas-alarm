from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def alert_history(request):
    alerts = request.user.alerts.all()
    return render(request, "alerts.html", {"alerts": alerts})
