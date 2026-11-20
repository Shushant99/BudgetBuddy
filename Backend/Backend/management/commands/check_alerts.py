from django.core.management.base import BaseCommand

from Backend.alert_jobs import run_alert_check


class Command(BaseCommand):
    help = (
        'Creates the calendar-based alerts (budget ending soon, savings goal due or overdue) for every user '
        'and emails them. Run it once a day, so people are told even if they do not open the app.'
    )

    def handle(self, *args, **options):
        result = run_alert_check()
        for problem in result['skipped']:
            self.stderr.write(f'Skipped {problem}')
        self.stdout.write(self.style.SUCCESS(
            f"Checked {result['checked']} users: {result['new_alerts']} new alerts, {result['emailed']} emailed."
        ))