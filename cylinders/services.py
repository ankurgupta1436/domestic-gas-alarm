from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from django.utils import timezone

from .models import Cylinder


@dataclass(frozen=True)
class GasStatus:
    started: bool
    start_date: date | None
    initial_kg: Decimal
    total_days: int
    current_day: int
    days_left: int
    current_percent: Decimal
    current_kg: Decimal
    empty_date: date | None
    source: str


def get_active_cylinder(user) -> Cylinder | None:
    return user.cylinders.filter(is_active=True).first()


def calculate_gas_status(cylinder: Cylinder | None) -> GasStatus:
    if cylinder is None:
        return GasStatus(
            started=False,
            start_date=None,
            initial_kg=Decimal("14.2"),
            total_days=501,
            current_day=0,
            days_left=501,
            current_percent=Decimal("100"),
            current_kg=Decimal("14.2"),
            empty_date=None,
            source="Not started",
        )

    start_date = cylinder.start_date
    total_days = max(int(cylinder.total_days), 1)
    today = timezone.localdate()
    current_day = max((today - start_date).days + 1, 1)
    days_left = max(total_days - current_day, 0)
    remaining_percent = max(
        Decimal("100") - (Decimal(current_day - 1) / Decimal(total_days) * Decimal("100")),
        Decimal("0"),
    )
    initial_kg = cylinder.initial_kg
    current_kg = (initial_kg * remaining_percent / Decimal("100")).quantize(Decimal("0.01"))
    empty_date = start_date + timedelta(days=total_days - 1)
    current_day = min(current_day, total_days)

    return GasStatus(
        started=True,
        start_date=start_date,
        initial_kg=initial_kg,
        total_days=total_days,
        current_day=current_day,
        days_left=days_left,
        current_percent=remaining_percent.quantize(Decimal("0.01")),
        current_kg=current_kg,
        empty_date=empty_date,
        source=(
            f"Started on {start_date.strftime('%d-%m-%Y')} | "
            f"Day {current_day} of {total_days}"
        ),
    )


def start_tracking(user, start_date: date, initial_kg: Decimal, total_days: int) -> Cylinder:
    user.cylinders.filter(is_active=True).update(is_active=False)
    return Cylinder.objects.create(
        user=user,
        start_date=start_date,
        initial_kg=initial_kg,
        total_days=total_days,
        is_active=True,
    )
