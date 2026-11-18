"""Emails an alert to the user it belongs to."""
import logging
import threading

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import connection
from django.utils import timezone
from django.utils.html import escape

from Backend.models import Notification, Profile

logger = logging.getLogger(__name__)

COLORS = {'info': '#5b5bf0', 'success': '#16a34a', 'warning': '#f59e0b', 'danger': '#dc2626'}


def is_configured():
    """True when emails really go out (SMTP); otherwise they are only printed in the terminal."""
    return settings.EMAIL_BACKEND.endswith('smtp.EmailBackend')


def wants_email(user, kind, level, force=None):
    """Should this alert also be emailed, according to the user's settings?

    force=False never emails, force=True always emails (if alerts are on), None decides by level:
    warnings and dangers are emailed. Income / expense receipts follow their own switch.
    """
    if force is False or not user.email:
        return False
    profile, _ = Profile.objects.get_or_create(user=user)
    if not profile.email_alerts:
        return False
    if kind in (Notification.Kind.INCOME, Notification.Kind.EXPENSE):
        return profile.email_transactions
    return bool(force) or level in (Notification.Level.WARNING, Notification.Level.DANGER)


def render(name, title, message, link, level):
    """(subject, plain text, html) for one alert. Everything a user can type is HTML-escaped."""
    title = ' '.join(str(title).split())  # one line only: it also goes into the subject header
    url = settings.APP_URL + (link or '/notifications')
    settings_url = settings.APP_URL + '/notifications'
    subject = f'[Budget Buddy] {title}'[:200]
    color = COLORS.get(level, COLORS['info'])

    text = (
        f'Hi {name},\n\n{title}\n{message}\n\nOpen Budget Buddy: {url}\n\n--\n'
        f'You get this email because email alerts are on for your account.\n'
        f'To change that, open {settings_url}\n'
    )
    html = f"""<!doctype html>
<html><body style="margin:0;padding:24px;background:#f4f5fb;font-family:Arial,Helvetica,sans-serif;color:#1c1f33;">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0"><tr><td align="center">
<table role="presentation" width="520" cellspacing="0" cellpadding="0" style="max-width:520px;background:#ffffff;border-radius:12px;border-top:5px solid {color};">
<tr><td style="padding:28px 28px 8px;font-size:13px;color:#6b7090;">Budget Buddy</td></tr>
<tr><td style="padding:0 28px;font-size:14px;color:#6b7090;">Hi {escape(name)},</td></tr>
<tr><td style="padding:12px 28px 4px;font-size:20px;font-weight:bold;color:#1c1f33;">{escape(title)}</td></tr>
<tr><td style="padding:4px 28px 20px;font-size:15px;line-height:1.5;color:#1c1f33;">{escape(message)}</td></tr>
<tr><td style="padding:0 28px 28px;"><a href="{escape(url)}" style="display:inline-block;padding:11px 20px;background:{color};color:#ffffff;text-decoration:none;border-radius:8px;font-size:14px;font-weight:bold;">Open Budget Buddy</a></td></tr>
<tr><td style="padding:16px 28px;border-top:1px solid #e6e8f2;font-size:12px;line-height:1.5;color:#6b7090;">You get this email because email alerts are on for your account. <a href="{escape(settings_url)}" style="color:#5b5bf0;">Change your email settings</a>.</td></tr>
</table></td></tr></table></body></html>"""
    return subject, text, html


def _message(user, title, message, link, level):
    subject, text, html = render(user.first_name or 'there', title, message, link, level)
    mail = EmailMultiAlternatives(
        subject, text, settings.DEFAULT_FROM_EMAIL, [user.email],
        headers={'Auto-Submitted': 'auto-generated'},
    )
    mail.attach_alternative(html, 'text/html')
    return mail


def _deliver(notification_id, in_thread):
    try:
        n = Notification.objects.select_related('user').get(pk=notification_id)
        sent = _message(
            n.user,
            n.title,
            n.message,
            n.link,
            n.level
        ).send()

        if sent:
            Notification.objects.filter(pk=n.pk).update(
            emailed_at=timezone.now()
            )
        else:
            logger.warning(
                'Email was not sent for notification %s',
                notification_id
            )
    except Exception:
        logger.exception('Could not email notification %s', notification_id)
    finally:
        if in_thread:
            connection.close()  # a background thread has its own database connection


def send_alert_email(notification, force=None):
    """Email a notification to its owner if their settings allow it. Never raises."""
    try:
        if not wants_email(notification.user, notification.kind, notification.level, force):
            return
        if getattr(settings, 'ALERT_EMAILS_ASYNC', True):
            threading.Thread(target=_deliver, args=(notification.pk, True)).start()
        else:
            _deliver(notification.pk, False)
    except Exception:
        logger.exception('Could not queue email for notification %s', getattr(notification, 'pk', None))


def send_test_email(user):
    """Send a sample alert right now. Raises if the mail server refuses it."""
    _message(
        user, 'This is a test email',
        'If you can read this, Budget Buddy can email your alerts to this address.', '/notifications', 'success',
    ).send()