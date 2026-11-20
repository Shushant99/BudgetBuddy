from django.contrib.auth import get_user_model
from django.db.models import Max

from Backend.emails import send_now
from Backend.models import Notification
from Backend.notifications import sync_time_based_alerts


def run_alert_check():
    """Create the calendar-based alerts (budget ending soon, goal due or overdue) for every user and email them.

    Returns how many users were checked and how many new alerts / emails that produced.
    """
    last_id = Notification.objects.aggregate(m=Max('id'))['m'] or 0
    checked, skipped = 0, []
    with send_now():
        for user in get_user_model().objects.filter(is_active=True).iterator():
            try:
                sync_time_based_alerts(user)
                checked += 1
            except Exception as exc:  # one broken account must not stop everyone else's alerts
                skipped.append(f'user {user.pk}: {exc}')

    created = Notification.objects.filter(id__gt=last_id)
    return {
        'checked': checked,
        'new_alerts': created.count(),
        'emailed': created.exclude(emailed_at=None).count(),
        'skipped': skipped,
    }