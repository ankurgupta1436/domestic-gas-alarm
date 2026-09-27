from __future__ import annotations

import logging

import requests
from django.conf import settings
from django.core.mail import send_mail
from django.db import IntegrityError
from django.utils import timezone

from accounts.models import UserProfile
from alerts.models import Alert, AlertDeliveryStatus
from cylinders.models import Cylinder
from cylinders.services import GasStatus, calculate_gas_status

logger = logging.getLogger(__name__)


def build_alert_message(gas: GasStatus) -> str:
    if gas.days_left == 0:
        timing = "today"
    elif gas.days_left == 1:
        timing = "tomorrow"
    else:
        timing = f"in {gas.days_left} days"

    return (
        f"Alert: Your domestic gas cylinder is expected to finish {timing}. "
        f"Current level is {gas.current_percent}% ({gas.current_kg} kg). "
        "Please book a refill."
    )


def send_email_alert(recipient: str, subject: str, message: str) -> AlertDeliveryStatus:
    if not recipient:
        return AlertDeliveryStatus.SKIPPED

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,       #fail_silently=False,
        )
        return AlertDeliveryStatus.SENT
    except Exception:
        logger.exception("Failed to send email alert to %s", recipient)
        return AlertDeliveryStatus.FAILED


def send_sms_alert(phone: str, message: str) -> AlertDeliveryStatus:
    phone = phone.strip()
    if not phone:
        return AlertDeliveryStatus.SKIPPED

    api_key = settings.FAST2SMS_API_KEY
    if not api_key:
        logger.info("FAST2SMS_API_KEY not set; skipping SMS to %s", phone)
        return AlertDeliveryStatus.SKIPPED

    try:
        response = requests.post(
            "https://www.fast2sms.com/dev/bulkV2",
            headers={"authorization": api_key},
            data={
                "route": "q",
                "message": message,
                "language": "english",
                "numbers": "".join(ch for ch in phone if ch.isdigit())[-10:],
            },
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("return", payload.get("status")) is True or payload.get("status") == "OK":
            return AlertDeliveryStatus.SENT
        logger.error("Fast2SMS rejected SMS: %s", payload)
        return AlertDeliveryStatus.FAILED
    except Exception:
        logger.exception("Failed to send SMS alert to %s", phone)
        return AlertDeliveryStatus.FAILED


def summarize_delivery(email_status: str, sms_status: str) -> str:
    statuses = {email_status, sms_status}
    if statuses <= {AlertDeliveryStatus.SKIPPED}:
        return AlertDeliveryStatus.SKIPPED
    if AlertDeliveryStatus.SENT in statuses and statuses <= {
        AlertDeliveryStatus.SENT,
        AlertDeliveryStatus.SKIPPED,
    }:
        return AlertDeliveryStatus.SENT
    if AlertDeliveryStatus.SENT in statuses:
        return AlertDeliveryStatus.PARTIAL
    return AlertDeliveryStatus.FAILED


def send_alert_if_needed(user, cylinder: Cylinder | None, profile: UserProfile) -> Alert | None:
    gas = calculate_gas_status(cylinder)
    if not gas.started:
        return None

    alert_window = max(int(profile.alert_days_before), 0)
    if gas.days_left > alert_window:
        return None

    reason_key = f"empty-warning-{timezone.localdate().isoformat()}"
    if Alert.objects.filter(user=user, reason_key=reason_key).exists():
        return None

    message = build_alert_message(gas)
    subject = "Domestic Gas Alarm — refill reminder"

    email_status = send_email_alert(profile.alert_email, subject, message)
    primary_sms = send_sms_alert(profile.phone, message)
    alternate_sms = send_sms_alert(profile.alternate_phone, message)

    if primary_sms == AlertDeliveryStatus.SENT or alternate_sms == AlertDeliveryStatus.SENT:
        sms_status = AlertDeliveryStatus.SENT
    elif primary_sms == AlertDeliveryStatus.SKIPPED and alternate_sms == AlertDeliveryStatus.SKIPPED:
        sms_status = AlertDeliveryStatus.SKIPPED
    elif primary_sms == AlertDeliveryStatus.FAILED and alternate_sms == AlertDeliveryStatus.FAILED:
        sms_status = AlertDeliveryStatus.FAILED
    else:
        sms_status = AlertDeliveryStatus.PARTIAL

    overall = summarize_delivery(email_status, sms_status)

    try:
        return Alert.objects.create(
            user=user,
            cylinder=cylinder,
            reason_key=reason_key,
            message=message,
            channels="Email, SMS",
            phone=profile.phone,
            alternate_phone=profile.alternate_phone,
            email=profile.alert_email,
            email_status=email_status,
            sms_status=sms_status,
            status=overall,
        )
    except IntegrityError:
        logger.info("Duplicate alert skipped for %s (%s)", user.username, reason_key)
        return None


def process_user_alerts(user) -> Alert | None:
    profile, _ = UserProfile.objects.get_or_create(user=user)
    cylinder = user.cylinders.filter(is_active=True).first()
    return send_alert_if_needed(user, cylinder, profile)




import resend

def send_email_alert(recipient, subject, message):
    if not recipient:
        return AlertDeliveryStatus.SKIPPED
    try:
        resend.api_key = settings.RESEND_API_KEY
        resend.Emails.send({
            "from": "Domestic Gas Alarm <onboarding@resend.dev>",
            "to": [recipient],
            "subject": subject,
            "text": message,
        })
        return AlertDeliveryStatus.SENT
    except Exception as e:
        logger.error("Email FAILED: %s", e)
        return AlertDeliveryStatus.FAILED