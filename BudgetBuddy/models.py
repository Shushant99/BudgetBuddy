from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    phone_number = models.CharField(max_length=30, blank=True)
    date_of_birth = models.DateField(blank=True, null=True)
    preferred_currency = models.CharField(max_length=3, default='INR')
    is_premium = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Profile for {self.user}'


class PremiumUpgradeRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='premium_upgrade_requests',
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(blank=True, null=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='reviewed_premium_requests',
    )

    class Meta:
        ordering = ['-requested_at', '-id']
        constraints = [
            models.UniqueConstraint(
                fields=['user'],
                name='one_premium_request_per_user',
            ),
        ]

    def __str__(self):
        return f'Premium request from {self.user} ({self.get_status_display()})'


class Income(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='incomes',
    )
    source = models.CharField(max_length=100)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
    )
    received_on = models.DateField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-received_on', '-id']
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name='income_amount_positive',
            ),
        ]

    def __str__(self):
        return f'{self.source}: {self.amount}'


class Expense(models.Model):
    class Category(models.TextChoices):
        HOUSING = 'housing', 'Housing'
        FOOD = 'food', 'Food'
        TRANSPORT = 'transport', 'Transport'
        UTILITIES = 'utilities', 'Utilities'
        HEALTHCARE = 'healthcare', 'Healthcare'
        ENTERTAINMENT = 'entertainment', 'Entertainment'
        SHOPPING = 'shopping', 'Shopping'
        EDUCATION = 'education', 'Education'
        OTHER = 'other', 'Other'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='expenses',
    )
    category = models.CharField(max_length=20, choices=Category.choices)
    description = models.CharField(max_length=200, blank=True)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
    )
    spent_on = models.DateField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-spent_on', '-id']
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name='expense_amount_positive',
            ),
        ]

    def __str__(self):
        return f'{self.get_category_display()}: {self.amount}'


class Budget(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='budgets',
    )
    category = models.CharField(max_length=20, choices=Expense.Category.choices)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
    )
    start_date = models.DateField()
    end_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date', 'category']
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name='budget_amount_positive',
            ),
            models.CheckConstraint(
                condition=Q(end_date__gte=models.F('start_date')),
                name='budget_end_on_or_after_start',
            ),
            models.UniqueConstraint(
                fields=['user', 'category', 'start_date', 'end_date'],
                name='unique_budget_category_period_per_user',
            ),
        ]

    def __str__(self):
        return f'{self.get_category_display()} budget: {self.amount}'


class SavingsGoal(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        PAUSED = 'paused', 'Paused'
        COMPLETED = 'completed', 'Completed'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='savings_goals',
    )
    name = models.CharField(max_length=100)
    target_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
    )
    current_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )
    target_date = models.DateField(blank=True, null=True)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['target_date', 'name']
        constraints = [
            models.CheckConstraint(
                condition=Q(target_amount__gt=0),
                name='savings_target_amount_positive',
            ),
            models.CheckConstraint(
                condition=Q(current_amount__gte=0),
                name='savings_current_amount_nonnegative',
            ),
        ]

    def __str__(self):
        return self.name


class SavingsContribution(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='savings_contributions',
    )
    goal = models.ForeignKey(
        SavingsGoal,
        on_delete=models.CASCADE,
        related_name='contributions',
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
    )
    contributed_on = models.DateField(default=timezone.localdate)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-contributed_on', '-id']
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name='savings_contribution_amount_positive',
            ),
        ]

    def __str__(self):
        return f'{self.amount} contributed to {self.goal}'


class Notification(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    title = models.CharField(max_length=150)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at', '-id']

    def __str__(self):
        return self.title


class Report(models.Model):
    class ReportType(models.TextChoices):
        MONTHLY = 'monthly', 'Monthly'
        ANNUAL = 'annual', 'Annual'
        CUSTOM = 'custom', 'Custom'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reports',
    )
    report_type = models.CharField(max_length=10, choices=ReportType.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    data = models.JSONField(default=dict, blank=True)
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-generated_at']
        constraints = [
            models.CheckConstraint(
                condition=Q(end_date__gte=models.F('start_date')),
                name='report_end_on_or_after_start',
            ),
        ]

    def __str__(self):
        return f'{self.get_report_type_display()} report for {self.user}'
