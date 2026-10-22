from django.contrib import admin

from BudgetBuddy.models import (
    Budget,
    Expense,
    Income,
    Notification,
    Profile,
    Report,
    SavingsGoal,
)


admin.site.register(
    [Profile, Income, Expense, Budget, SavingsGoal, Notification, Report]
)
