"""Creates in-app notifications: money in/out, budgets, savings goals and account events."""
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone
from Backend.emails import send_alert_email
from Backend.models import (
    Budget, Expense, Income, Notification, PremiumUpgradeRequest, SavingsContribution, SavingsGoal,
)

K = Notification.Kind
L = Notification.Level

BUDGET_WARNING_RATIO = Decimal('0.8')  # warn when 80% of a budget has been used
BUDGET_ENDING_DAYS = 3                 # tell the user when a budget ends within this many days
GOAL_DUE_DAYS = 7                      # ...and when a savings goal's target date is this close
MAX_PER_USER = 200                     # older notifications are removed beyond this


# ---------- helpers ----------
def rupees(value):
    value = Decimal(value)
    return f"{'-' if value < 0 else ''}₹{abs(value):,.2f}"


def fmt_date(d):
    return f'{d.day} {d:%b %Y}'


def in_days(days):
    return 'today' if days == 0 else f"in {days} day{'' if days == 1 else 's'}"


def available_balance(user):
    """Income minus expenses minus savings, for everything dated up to today (matches the dashboard)."""
    today = timezone.localdate()

    def total(model, field):
        return model.objects.filter(user=user, **{f'{field}__lte': today}).aggregate(t=Sum('amount'))['t'] or 0

    return total(Income, 'received_on') - total(Expense, 'spent_on') - total(SavingsContribution, 'contributed_on')


def budget_spent(budget, today):
    return Expense.objects.filter(
        user=budget.user, category=budget.category, spent_on__gte=budget.start_date, spent_on__lte=today,
    ).aggregate(t=Sum('amount'))['t'] or 0


def notify(user, kind, level, title, message='', link='', dedupe_key=None, email=None):
    """Create a notification. With a dedupe_key the same alert is only ever created once per user.

    The user is also emailed when their settings allow it: warnings and dangers by default,
    always when email=True, never when email=False (see emails.wants_email).
    """
    fields = {'kind': kind, 'level': level, 'title': title, 'message': message, 'link': link}
    if dedupe_key:
        obj, created = Notification.objects.get_or_create(user=user, dedupe_key=dedupe_key, defaults=fields)
        if not created:
            return None
    else:
        obj = Notification.objects.create(user=user, **fields)

    stale = list(
        Notification.objects.filter(user=user).order_by('-created_at', '-id').values_list('id', flat=True)[MAX_PER_USER:]
    )
    if stale:
        Notification.objects.filter(id__in=stale).delete()
    send_alert_email(obj, email)
    return obj


# ---------- warnings ----------
def check_budget_alerts(user, category, added=None, on_date=None):
    """Warn when spending reaches 80% of a budget, or goes past it.

    `added` is an amount that was just spent: alerts only fire when it carries the total over
    a threshold. Without it (e.g. a brand-new budget) the current state is checked instead.
    """
    today = timezone.localdate()
    budgets = Budget.objects.filter(user=user, category=category, start_date__lte=today, end_date__gte=today)
    for b in budgets:
        if added is not None and not (b.start_date <= (on_date or today) <= today):
            continue  # that expense does not count towards this budget
        spent = budget_spent(b, today)
        before = None if added is None else spent - added

        def crossed(limit, strict=False):
            reached = spent > limit if strict else spent >= limit
            was = before is not None and (before > limit if strict else before >= limit)
            return reached and not was

        label = b.get_category_display()
        if crossed(b.amount, strict=True):
            notify(
                user, K.BUDGET, L.DANGER, f'{label} budget exceeded',
                f'You have spent {rupees(spent)} of your {rupees(b.amount)} budget, {rupees(spent - b.amount)} over.',
                '/dashboard', f'budget:{b.id}:over',
            )
        elif crossed(b.amount * BUDGET_WARNING_RATIO):
            notify(
                user, K.BUDGET, L.WARNING, f'{label} budget is {int(spent / b.amount * 100)}% used',
                f'Only {rupees(b.amount - spent)} left of your {rupees(b.amount)} budget.',
                '/dashboard', f'budget:{b.id}:warn',
            )


def check_overspend(user, amount, on_date=None):
    """Warn when a payment tips the available balance below zero."""
    if on_date and on_date > timezone.localdate():
        return
    balance = available_balance(user)
    if balance < 0 <= balance + amount:
        notify(
            user, K.WARNING, L.DANGER, 'You are spending more than you have',
            f'You are {rupees(-balance)} short. Add income or review your spending.',
            '/dashboard',
        )


# ---------- events ----------
def notify_income(user, income):
    today = timezone.localdate()
    if income.received_on <= today:
        message = f'Your available balance is now {rupees(available_balance(user))}.'
    else:
        message = f'Scheduled for {fmt_date(income.received_on)}.'
    notify(
        user, K.INCOME, L.SUCCESS, f'{rupees(income.amount)} received from {income.source}',
        message, '/transactions',
    )


def notify_expense(user, expense):
    notify(
        user, K.EXPENSE, L.INFO, f'{rupees(expense.amount)} spent on {expense.get_category_display()}',
        expense.description or f'Recorded for {fmt_date(expense.spent_on)}.', '/transactions',
    )
    if expense.spent_on <= timezone.localdate():
        check_budget_alerts(user, expense.category, added=expense.amount, on_date=expense.spent_on)
    check_overspend(user, expense.amount, expense.spent_on)


def notify_budget_created(user, budget):
    notify(
        user, K.BUDGET, L.INFO, f'{budget.get_category_display()} budget set: {rupees(budget.amount)}',
        f'Runs from {fmt_date(budget.start_date)} to {fmt_date(budget.end_date)}.', '/dashboard',
    )
    check_budget_alerts(user, budget.category)


def notify_budget_paid(user, budget, amount):
    notify(
        user, K.BUDGET, L.SUCCESS, f'{budget.get_category_display()} budget paid',
        f'{rupees(amount)} was recorded as an expense.', '/transactions',
    )
    check_overspend(user, amount)


def notify_contribution(user, goal, amount):
    left = goal.target_amount - goal.current_amount
    if goal.status == SavingsGoal.Status.COMPLETED:
        notify(
            user, K.SAVINGS, L.SUCCESS, f'Goal reached: {goal.name}',
            f'Your {rupees(amount)} completed the {rupees(goal.target_amount)} goal. Well done!', '/savings-goals',
        )
    else:
        pct = min(int(goal.current_amount / goal.target_amount * 100), 100)
        notify(
            user, K.SAVINGS, L.SUCCESS, f'{rupees(amount)} saved to {goal.name}',
            f'{pct}% of your {rupees(goal.target_amount)} goal. {rupees(left)} to go.', '/savings-goals',
        )
    check_overspend(user, amount)


def notify_premium(user, status):
    if status == PremiumUpgradeRequest.Status.PENDING:
        notify(user, K.ACCOUNT, L.INFO, 'Premium request received',
               'An administrator will review it soon.', '/dashboard')
    elif status == PremiumUpgradeRequest.Status.APPROVED:
        notify(user, K.ACCOUNT, L.SUCCESS, 'Premium is now on',
               'Your upgrade request was approved. Money insights are unlocked.', '/dashboard',email=True)
    elif status == PremiumUpgradeRequest.Status.REJECTED:
        notify(user, K.ACCOUNT, L.WARNING, 'Premium request declined',
               'Your upgrade request was not approved. You can request it again from the dashboard.', '/dashboard')


def notify_for_record(user, record_type, obj):
    """Called after a record is added from the Add record page."""
    if record_type == 'income':
        notify_income(user, obj)
    elif record_type == 'expense':
        notify_expense(user, obj)
    elif record_type == 'budget':
        notify_budget_created(user, obj)


# ---------- time-based alerts ----------
def sync_time_based_alerts(user):
    """Alerts that depend on the calendar rather than on something the user just did.

    Safe to call often: every alert is created once (see dedupe_key).
    """
    today = timezone.localdate()

    budgets = Budget.objects.filter(
        user=user, start_date__lte=today, end_date__gte=today, paid_expense__isnull=True,
    )
    for b in budgets:
        days_left = (b.end_date - today).days
        if days_left > BUDGET_ENDING_DAYS:
            continue
        left = b.amount - budget_spent(b, today)
        if left > 0:
            notify(
                user, K.BUDGET, L.INFO, f'{b.get_category_display()} budget ends {in_days(days_left)}',
                f'{rupees(left)} of your {rupees(b.amount)} budget is still unspent.',
                '/dashboard', f'budget:{b.id}:ending', email=True,
            )

    goals = SavingsGoal.objects.filter(user=user, status=SavingsGoal.Status.ACTIVE, target_date__isnull=False)
    for g in goals:
        to_go = g.target_amount - g.current_amount
        days_left = (g.target_date - today).days
        if to_go <= 0:
            continue
        if days_left < 0:
            notify(
                user, K.SAVINGS, L.DANGER, f'{g.name} is past its target date',
                f'You still need {rupees(to_go)}. Add savings or move the date.',
                '/savings-goals', f'goal:{g.id}:overdue',
            )
        elif days_left <= GOAL_DUE_DAYS:
            notify(
                user, K.SAVINGS, L.WARNING, f'{g.name} is due {in_days(days_left)}',
                f'{rupees(to_go)} still to save.', '/savings-goals', f'goal:{g.id}:due',
            )