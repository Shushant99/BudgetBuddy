from datetime import datetime, timezone as datetime_timezone
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from BudgetBuddy.models import (
    Budget,
    Expense,
    Income,
    PremiumUpgradeRequest,
    Profile,
    SavingsContribution,
    SavingsGoal,
)


class PremiumUpgradeRequestTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='student',
            email='student@example.com',
            password='test-password',
        )
        Profile.objects.create(user=self.user)
        self.client.force_login(self.user)

    def test_request_is_created_once_and_can_be_resubmitted_after_rejection(self):
        url = reverse('request_premium_upgrade')

        self.client.post(url)
        self.client.post(url)
        self.assertEqual(PremiumUpgradeRequest.objects.filter(user=self.user).count(), 1)
        upgrade_request = PremiumUpgradeRequest.objects.get(user=self.user)
        self.assertEqual(upgrade_request.status, PremiumUpgradeRequest.Status.PENDING)

        upgrade_request.status = PremiumUpgradeRequest.Status.REJECTED
        upgrade_request.save(update_fields=('status',))
        response = self.client.post(url)

        upgrade_request.refresh_from_db()
        self.assertRedirects(response, reverse('Dashboard'))
        self.assertEqual(upgrade_request.status, PremiumUpgradeRequest.Status.PENDING)

    def test_premium_user_cannot_submit_upgrade_request(self):
        Profile.objects.filter(user=self.user).update(is_premium=True)

        self.client.post(reverse('request_premium_upgrade'))

        self.assertFalse(
            PremiumUpgradeRequest.objects.filter(user=self.user).exists(),
        )

    def test_admin_approval_enables_premium(self):
        admin_user = get_user_model().objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin-password',
        )
        upgrade_request = PremiumUpgradeRequest.objects.create(user=self.user)
        self.client.force_login(admin_user)

        response = self.client.post(
            '/admin/budgetbuddy/premiumupgraderequest/',
            {
                'action': 'approve_requests',
                '_selected_action': str(upgrade_request.pk),
                'index': '0',
            },
        )

        self.assertEqual(response.status_code, 302)
        upgrade_request.refresh_from_db()
        self.assertEqual(upgrade_request.status, PremiumUpgradeRequest.Status.APPROVED)
        self.assertTrue(Profile.objects.get(user=self.user).is_premium)


class AddRecordTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='entry-user',
            email='entry@example.com',
            password='test-password',
        )
        self.client.force_login(self.user)

    def test_add_record_page_requires_login(self):
        self.client.logout()

        response = self.client.get(reverse('add_record'))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

    def test_add_record_page_shows_type_selector_and_fields(self):
        response = self.client.get(reverse('add_record'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'What would you like to add?')
        self.assertContains(response, 'Savings goal')
        self.assertContains(response, 'source')
        self.assertContains(response, 'target_amount')

    def test_income_is_saved_for_the_signed_in_user(self):
        response = self.client.post(
            reverse('add_record'),
            {
                'record_type': 'income',
                'source': 'Part-time work',
                'amount': '450.00',
                'received_on': '2026-10-05',
                'notes': 'October pay',
            },
        )

        self.assertRedirects(response, reverse('Dashboard'))
        income = Income.objects.get(source='Part-time work')
        self.assertEqual(income.user, self.user)
        self.assertEqual(income.amount, 450)

    def test_expense_is_saved_with_its_selected_category(self):
        response = self.client.post(
            reverse('add_record'),
            {
                'record_type': 'expense',
                'category': Expense.Category.FOOD,
                'description': 'Groceries',
                'amount': '32.50',
                'spent_on': '2026-10-06',
                'notes': '',
            },
        )

        self.assertRedirects(response, reverse('Dashboard'))
        expense = Expense.objects.get(description='Groceries')
        self.assertEqual(expense.user, self.user)
        self.assertEqual(expense.category, Expense.Category.FOOD)

    def test_budget_and_savings_goal_are_saved_for_user(self):
        self.client.post(
            reverse('add_record'),
            {
                'record_type': 'budget',
                'category': Expense.Category.FOOD,
                'amount': '200.00',
                'start_date': '2026-10-01',
                'end_date': '2026-10-31',
            },
        )
        self.client.post(
            reverse('add_record'),
            {
                'record_type': 'goal',
                'name': 'Emergency fund',
                'target_amount': '1000.00',
                'current_amount': '100.00',
                'target_date': '2027-10-01',
            },
        )

        self.assertEqual(Budget.objects.get(user=self.user).amount, 200)
        goal = SavingsGoal.objects.get(name='Emergency fund')
        self.assertEqual(goal.user, self.user)
        self.assertEqual(goal.status, SavingsGoal.Status.ACTIVE)

    def test_invalid_amount_does_not_create_record(self):
        response = self.client.post(
            reverse('add_record'),
            {
                'record_type': 'income',
                'source': 'Part-time work',
                'amount': '0',
                'received_on': '2026-10-05',
                'notes': '',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ensure this value is greater than or equal to 0.01.')
        self.assertFalse(Income.objects.exists())

    def test_dashboard_reflects_new_records_and_displays_rupees(self):
        today = timezone.localdate()
        self.client.post(
            reverse('add_record'),
            {
                'record_type': 'income',
                'source': 'Current month income',
                'amount': '450.00',
                'received_on': today.isoformat(),
                'notes': '',
            },
        )
        self.client.post(
            reverse('add_record'),
            {
                'record_type': 'expense',
                'category': Expense.Category.FOOD,
                'description': 'Current month expense',
                'amount': '50.00',
                'spent_on': today.isoformat(),
                'notes': '',
            },
        )

        response = self.client.get(reverse('Dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['monthly_income'], 450)
        self.assertEqual(response.context['monthly_expenses'], 50)
        self.assertEqual(response.context['monthly_balance'], 400)
        self.assertContains(response, '₹ 450.00')
        self.assertContains(response, '₹ 50.00')
        self.assertContains(response, '₹ 400.00')
        self.assertEqual(Profile.objects.get(user=self.user).preferred_currency, 'INR')

    def test_dashboard_uses_neutral_account_label_for_staff(self):
        self.user.is_staff = True
        self.user.save(update_fields=('is_staff',))

        response = self.client.get(reverse('Dashboard'))

        self.assertContains(response, 'Account overview')
        self.assertContains(response, 'Administration')
        self.assertNotContains(response, 'Student account')
        self.assertNotContains(response, 'YOUR STUDENT MONEY HUB')

    @override_settings(TIME_ZONE='Asia/Kolkata')
    @patch(
        'django.utils.timezone.now',
        return_value=datetime(2026, 10, 23, 19, 0, tzinfo=datetime_timezone.utc),
    )
    def test_local_today_record_is_included_after_utc_midnight(self, _mock_now):
        self.client.post(
            reverse('add_record'),
            {
                'record_type': 'income',
                'source': 'Today in India',
                'amount': '125.00',
                'received_on': '2026-10-24',
                'notes': '',
            },
        )

        response = self.client.get(reverse('Dashboard'))

        self.assertTrue(_mock_now.called)
        self.assertEqual(response.context['today'].isoformat(), '2026-10-24')
        self.assertEqual(response.context['monthly_income'], 125)


class TransactionHistoryTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='history-user',
            email='history@example.com',
            password='test-password',
        )
        self.other_user = user_model.objects.create_user(
            username='other-history-user',
            email='other-history@example.com',
            password='test-password',
        )
        self.client.force_login(self.user)
        Income.objects.create(
            user=self.user,
            source='Salary',
            amount='1000.00',
            received_on='2026-10-10',
        )
        Expense.objects.create(
            user=self.user,
            category=Expense.Category.FOOD,
            description='Groceries',
            amount='75.00',
            spent_on='2026-10-12',
        )
        Income.objects.create(
            user=self.other_user,
            source='Private income',
            amount='9000.00',
            received_on='2026-10-11',
        )

    def test_history_shows_all_current_users_income_and_expenses(self):
        response = self.client.get(reverse('transaction_history'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page_obj'].paginator.count, 2)
        self.assertContains(response, 'Salary')
        self.assertContains(response, 'Groceries')
        self.assertNotContains(response, 'Private income')

    def test_history_filters_by_type_and_date_range(self):
        response = self.client.get(
            reverse('transaction_history'),
            {
                'record_type': 'income',
                'from_date': '2026-10-09',
                'to_date': '2026-10-11',
            },
        )

        self.assertEqual(response.context['page_obj'].paginator.count, 1)
        self.assertContains(response, 'Salary')
        self.assertNotContains(response, 'Groceries')

    def test_history_paginates_and_preserves_filters(self):
        Income.objects.bulk_create([
            Income(
                user=self.user,
                source=f'Income {index}',
                amount='10.00',
                received_on='2026-10-10',
            )
            for index in range(25)
        ])

        response = self.client.get(
            reverse('transaction_history'),
            {'record_type': 'income', 'page': '2'},
        )

        self.assertEqual(response.context['page_obj'].paginator.count, 26)
        self.assertEqual(response.context['page_obj'].number, 2)
        self.assertContains(response, 'record_type=income&page=1')

    def test_invalid_date_range_shows_validation_error(self):
        response = self.client.get(
            reverse('transaction_history'),
            {'from_date': '2026-10-15', 'to_date': '2026-10-01'},
        )

        self.assertEqual(response.context['page_obj'].paginator.count, 0)
        self.assertContains(response, 'End date must be on or after the start date.')


class SavingsContributionTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='savings-user',
            email='savings@example.com',
            password='test-password',
        )
        self.other_user = user_model.objects.create_user(
            username='other-savings-user',
            email='other-savings@example.com',
            password='test-password',
        )
        self.goal = SavingsGoal.objects.create(
            user=self.user,
            name='Emergency fund',
            target_amount='500.00',
        )
        self.client.force_login(self.user)

    def test_savings_goals_have_a_dedicated_page_and_dashboard_has_no_contribution_form(self):
        goals_response = self.client.get(reverse('savings_goals'))
        dashboard_response = self.client.get(reverse('Dashboard'))

        self.assertEqual(goals_response.status_code, 200)
        self.assertContains(goals_response, 'Contribution amount')
        self.assertContains(goals_response, 'Create a goal')
        self.assertNotContains(dashboard_response, 'Add savings')
        self.assertContains(dashboard_response, 'Manage goals')

    def test_contribution_updates_goal_and_reduces_monthly_balance(self):
        Income.objects.create(
            user=self.user,
            source='Pay',
            amount='1000.00',
            received_on=timezone.localdate(),
        )

        response = self.client.post(
            reverse('contribute_to_savings_goal', args=[self.goal.pk]),
            {'amount': '125.00'},
        )

        self.assertRedirects(response, reverse('savings_goals'))
        self.goal.refresh_from_db()
        contribution = SavingsContribution.objects.get(goal=self.goal)
        self.assertEqual(self.goal.current_amount, 125)
        self.assertEqual(contribution.user, self.user)
        self.assertEqual(contribution.amount, 125)

        dashboard_response = self.client.get(reverse('Dashboard'))
        self.assertEqual(dashboard_response.context['monthly_savings'], 125)
        self.assertEqual(dashboard_response.context['monthly_balance'], 875)
        self.assertContains(dashboard_response, 'Savings contribution')

    def test_contribution_cannot_exceed_remaining_goal_amount(self):
        self.goal.current_amount = 450
        self.goal.save(update_fields=('current_amount',))

        response = self.client.post(
            reverse('contribute_to_savings_goal', args=[self.goal.pk]),
            {'amount': '75.00'},
            follow=True,
        )

        self.goal.refresh_from_db()
        self.assertEqual(self.goal.current_amount, 450)
        self.assertFalse(SavingsContribution.objects.exists())
        self.assertContains(response, 'Contribution cannot exceed this goal')

    def test_user_cannot_contribute_to_another_users_goal(self):
        other_goal = SavingsGoal.objects.create(
            user=self.other_user,
            name='Private goal',
            target_amount='300.00',
        )

        response = self.client.post(
            reverse('contribute_to_savings_goal', args=[other_goal.pk]),
            {'amount': '25.00'},
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(SavingsContribution.objects.exists())
        other_goal.refresh_from_db()
        self.assertEqual(other_goal.current_amount, 0)

    def test_reaching_goal_marks_it_completed(self):
        response = self.client.post(
            reverse('contribute_to_savings_goal', args=[self.goal.pk]),
            {'amount': '500.00'},
        )

        self.assertRedirects(response, reverse('savings_goals'))
        self.goal.refresh_from_db()
        self.assertEqual(self.goal.current_amount, 500)
        self.assertEqual(self.goal.status, SavingsGoal.Status.COMPLETED)

    def test_savings_contribution_can_be_filtered_in_transaction_history(self):
        SavingsContribution.objects.create(
            user=self.user,
            goal=self.goal,
            amount='50.00',
            contributed_on=timezone.localdate(),
        )

        response = self.client.get(
            reverse('transaction_history'),
            {'record_type': 'savings'},
        )

        self.assertEqual(response.context['page_obj'].paginator.count, 1)
        self.assertContains(response, 'Emergency fund')
        self.assertContains(response, 'Savings')
