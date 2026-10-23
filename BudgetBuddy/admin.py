from django.contrib import admin, messages
from django.db import transaction
from django.utils import timezone

from BudgetBuddy.models import (
    Budget,
    Expense,
    Income,
    Notification,
    PremiumUpgradeRequest,
    Profile,
    Report,
    SavingsContribution,
    SavingsGoal,
)


@admin.register(PremiumUpgradeRequest)
class PremiumUpgradeRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'requested_at', 'reviewed_at', 'reviewed_by')
    list_filter = ('status', 'requested_at')
    search_fields = ('user__username', 'user__email', 'user__first_name')
    readonly_fields = ('user', 'status', 'requested_at', 'reviewed_at', 'reviewed_by')
    actions = ('approve_requests', 'reject_requests')

    @admin.action(description='Approve selected requests and enable Premium')
    def approve_requests(self, request, queryset):
        pending = queryset.filter(status=PremiumUpgradeRequest.Status.PENDING)
        count = pending.count()
        with transaction.atomic():
            for upgrade_request in pending.select_related('user'):
                Profile.objects.update_or_create(
                    user=upgrade_request.user,
                    defaults={'is_premium': True},
                )
                upgrade_request.status = PremiumUpgradeRequest.Status.APPROVED
                upgrade_request.reviewed_at = timezone.now()
                upgrade_request.reviewed_by = request.user
                upgrade_request.save(
                    update_fields=('status', 'reviewed_at', 'reviewed_by'),
                )
        self.message_user(
            request,
            f'{count} request(s) approved and Premium enabled.',
            messages.SUCCESS,
        )

    @admin.action(description='Reject selected pending requests')
    def reject_requests(self, request, queryset):
        updated = queryset.filter(
            status=PremiumUpgradeRequest.Status.PENDING,
        ).update(
            status=PremiumUpgradeRequest.Status.REJECTED,
            reviewed_at=timezone.now(),
            reviewed_by=request.user,
        )
        self.message_user(
            request,
            f'{updated} pending request(s) rejected.',
            messages.SUCCESS,
        )


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'preferred_currency', 'is_premium', 'created_at')
    list_filter = ('is_premium', 'preferred_currency')
    search_fields = ('user__username', 'user__email', 'user__first_name')
    list_editable = ('is_premium',)


@admin.register(Income)
class IncomeAdmin(admin.ModelAdmin):
    list_display = ('source', 'user', 'amount', 'received_on')
    list_filter = ('received_on',)
    search_fields = ('source', 'user__email', 'notes')
    date_hierarchy = 'received_on'


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('description', 'category', 'user', 'amount', 'spent_on')
    list_filter = ('category', 'spent_on')
    search_fields = ('description', 'user__email', 'notes')
    date_hierarchy = 'spent_on'


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ('category', 'user', 'amount', 'start_date', 'end_date')
    list_filter = ('category', 'start_date')
    search_fields = ('user__email',)


@admin.register(SavingsGoal)
class SavingsGoalAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'current_amount', 'target_amount', 'status', 'target_date')
    list_filter = ('status',)
    search_fields = ('name', 'user__email')


@admin.register(SavingsContribution)
class SavingsContributionAdmin(admin.ModelAdmin):
    list_display = ('goal', 'user', 'amount', 'contributed_on', 'created_at')
    list_filter = ('contributed_on',)
    search_fields = ('goal__name', 'user__email')
    date_hierarchy = 'contributed_on'
    readonly_fields = ('user', 'goal', 'amount', 'contributed_on', 'created_at')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('title', 'message', 'user__email')


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('user', 'report_type', 'start_date', 'end_date', 'generated_at')
    list_filter = ('report_type', 'generated_at')
    search_fields = ('user__email',)


admin.site.site_header = 'Budget Buddy Administration'
admin.site.site_title = 'Budget Buddy Admin'
admin.site.index_title = 'Manage accounts and finances'
