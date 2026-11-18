from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db.models import Max

from Backend.models import Notification
from Backend.notifications import sync_time_based_alerts


class Command(BaseCommand):
    help = (
        'Creates the calendar-based alerts (budget ending soon, savings goal due or overdue) for every user '
        'and emails them. Run it once a day, so people are told even if they do not open the app.'
    )

    def handle(self, *args, **options):
        settings.ALERT_EMAILS_ASYNC = False  # send each email now, so the totals below are exact
        last_id = Notification.objects.aggregate(m=Max('id'))['m'] or 0

        users = get_user_model().objects.filter(is_active=True)
        checked = 0
        for user in users.iterator():
            try:
                sync_time_based_alerts(user)
                checked += 1
            except Exception as exc:  # one broken account must not stop everyone else's alerts
                self.stderr.write(f'Skipped user {user.pk}: {exc}')

        created = Notification.objects.filter(id__gt=last_id)
        self.stdout.write(self.style.SUCCESS(
            f'Checked {checked} users: {created.count()} new alerts, '
            f'{created.exclude(emailed_at=None).count()} emailed.'
        ))