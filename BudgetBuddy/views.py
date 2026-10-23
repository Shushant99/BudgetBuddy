from itertools import chain

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.core.paginator import Paginator
from django.db.models import F, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from BudgetBuddy.forms import (
    BudgetEntryForm,
    ExpenseEntryForm,
    IncomeEntryForm,
    RecordTypeForm,
    SavingsContributionForm,
    SavingsGoalEntryForm,
    SignupForm,
    TransactionFilterForm,
)
from BudgetBuddy.models import (
    Budget,
    Expense,
    Income,
    PremiumUpgradeRequest,
    Profile,
    SavingsContribution,
    SavingsGoal,
)


def signup(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            Profile.objects.create(user=user)
            messages.success(request, 'Your account has been created. You can now log in.')
            return redirect('login')
    else:
        form = SignupForm()

    return render(request, 'signup.html', {'form': form})


@login_required
def dashboard(request):
    today = timezone.localdate()
    month_start = today.replace(day=1)
    profile, _ = Profile.objects.get_or_create(user=request.user)

    expenses = Expense.objects.filter(
        user=request.user,
        spent_on__gte=month_start,
        spent_on__lte=today,
    )
    incomes = Income.objects.filter(
        user=request.user,
        received_on__gte=month_start,
        received_on__lte=today,
    )
    monthly_expenses = expenses.aggregate(total=Sum('amount'))['total'] or 0
    monthly_income = incomes.aggregate(total=Sum('amount'))['total'] or 0
    monthly_savings = SavingsContribution.objects.filter(
        user=request.user,
        contributed_on__gte=month_start,
        contributed_on__lte=today,
    ).aggregate(total=Sum('amount'))['total'] or 0

    budgets = Budget.objects.filter(
        user=request.user,
        start_date__lte=today,
        end_date__gte=today,
    )
    budget_rows = []
    for budget in budgets:
        spent = Expense.objects.filter(
            user=request.user,
            category=budget.category,
            spent_on__gte=budget.start_date,
            spent_on__lte=today,
        ).aggregate(total=Sum('amount'))['total'] or 0
        percent = min(round(float(spent / budget.amount * 100)), 100)
        budget_rows.append({
            'budget': budget,
            'spent': spent,
            'percent': percent,
            'remaining': max(budget.amount - spent, 0),
        })

    latest_expenses = [
        {
            'title': expense.description or expense.get_category_display(),
            'detail': expense.get_category_display(),
            'date': expense.spent_on,
            'amount': expense.amount,
            'kind': 'expense',
        }
        for expense in Expense.objects.filter(user=request.user)[:10]
    ]
    latest_incomes = [
        {
            'title': income.source,
            'detail': 'Income',
            'date': income.received_on,
            'amount': income.amount,
            'kind': 'income',
        }
        for income in Income.objects.filter(user=request.user)[:10]
    ]
    latest_savings = [
        {
            'title': contribution.goal.name,
            'detail': 'Savings contribution',
            'date': contribution.contributed_on,
            'amount': contribution.amount,
            'kind': 'savings',
        }
        for contribution in SavingsContribution.objects.filter(
            user=request.user,
        ).select_related('goal')[:10]
    ]
    transactions = sorted(
        chain(latest_expenses, latest_incomes, latest_savings),
        key=lambda item: item['date'],
        reverse=True,
    )[:10]

    category_spending = []
    if profile.is_premium:
        totals = expenses.values('category').annotate(total=Sum('amount')).order_by('-total')[:4]
        max_total = max((item['total'] for item in totals), default=0)
        category_labels = dict(Expense.Category.choices)
        category_spending = [
            {
                'label': category_labels[item['category']],
                'amount': item['total'],
                'percent': round(float(item['total'] / max_total * 100)) if max_total else 0,
            }
            for item in totals
        ]

    context = {
        'profile': profile,
        'local_now': timezone.localtime(),
        'upgrade_request': PremiumUpgradeRequest.objects.filter(
            user=request.user,
        ).first(),
        'today': today,
        'monthly_expenses': monthly_expenses,
        'monthly_income': monthly_income,
        'monthly_savings': monthly_savings,
        'monthly_balance': monthly_income - monthly_expenses - monthly_savings,
        'active_goals': SavingsGoal.objects.filter(
            user=request.user,
            status=SavingsGoal.Status.ACTIVE,
        )[:3],
        'budget_rows': budget_rows[:4],
        'budget_total': sum((row['budget'].amount for row in budget_rows), 0),
        'transactions': transactions,
        'category_spending': category_spending,
    }
    return render(request, 'Dashboard.html', context)


@login_required
def savings_goals(request):
    goals = SavingsGoal.objects.filter(
        user=request.user,
    ).annotate(
        remaining_amount=F('target_amount') - F('current_amount'),
    )
    return render(request, 'savings_goals.html', {
        'goals': goals,
        'active_goals': goals.filter(status=SavingsGoal.Status.ACTIVE),
        'completed_goals': goals.filter(status=SavingsGoal.Status.COMPLETED),
    })


@login_required
def contribute_to_savings_goal(request, goal_id):
    if request.method != 'POST':
        return redirect('savings_goals')

    form = SavingsContributionForm(request.POST)
    if not form.is_valid():
        messages.error(request, 'Enter a valid contribution amount greater than zero.')
        return redirect('savings_goals')

    with transaction.atomic():
        goal = get_object_or_404(
            SavingsGoal.objects.select_for_update(),
            pk=goal_id,
            user=request.user,
            status=SavingsGoal.Status.ACTIVE,
        )
        amount = form.cleaned_data['amount']
        remaining = goal.target_amount - goal.current_amount
        if amount > remaining:
            messages.error(
                request,
                f'Contribution cannot exceed this goal’s remaining amount of ₹{remaining:.2f}.',
            )
            return redirect('savings_goals')

        SavingsContribution.objects.create(
            user=request.user,
            goal=goal,
            amount=amount,
            contributed_on=timezone.localdate(),
        )
        goal.current_amount = F('current_amount') + amount
        fields_to_update = ['current_amount', 'updated_at']
        if amount == remaining:
            goal.status = SavingsGoal.Status.COMPLETED
            fields_to_update.append('status')
        goal.save(update_fields=fields_to_update)

    messages.success(
        request,
        f'₹{amount:.2f} added to {goal.name}.',
    )
    return redirect('savings_goals')


@login_required
def transaction_history(request):
    filter_data = request.GET.copy()
    if not filter_data.get('record_type'):
        filter_data['record_type'] = 'all'
    filter_form = TransactionFilterForm(filter_data)
    transactions = []

    if filter_form.is_valid():
        record_type = filter_form.cleaned_data.get('record_type') or 'all'
        from_date = filter_form.cleaned_data.get('from_date')
        to_date = filter_form.cleaned_data.get('to_date')

        if record_type in ('all', 'income'):
            incomes = Income.objects.filter(user=request.user)
            if from_date:
                incomes = incomes.filter(received_on__gte=from_date)
            if to_date:
                incomes = incomes.filter(received_on__lte=to_date)
            transactions.extend({
                'title': income.source,
                'detail': 'Income',
                'date': income.received_on,
                'amount': income.amount,
                'kind': 'income',
            } for income in incomes)

        if record_type in ('all', 'expense'):
            expenses = Expense.objects.filter(user=request.user)
            if from_date:
                expenses = expenses.filter(spent_on__gte=from_date)
            if to_date:
                expenses = expenses.filter(spent_on__lte=to_date)
            transactions.extend({
                'title': expense.description or expense.get_category_display(),
                'detail': expense.get_category_display(),
                'date': expense.spent_on,
                'amount': expense.amount,
                'kind': 'expense',
            } for expense in expenses)

        if record_type in ('all', 'savings'):
            contributions = SavingsContribution.objects.filter(
                user=request.user,
            ).select_related('goal')
            if from_date:
                contributions = contributions.filter(contributed_on__gte=from_date)
            if to_date:
                contributions = contributions.filter(contributed_on__lte=to_date)
            transactions.extend({
                'title': contribution.goal.name,
                'detail': 'Savings contribution',
                'date': contribution.contributed_on,
                'amount': contribution.amount,
                'kind': 'savings',
            } for contribution in contributions)

        transactions.sort(key=lambda item: item['date'], reverse=True)

    page_obj = Paginator(transactions, 25).get_page(request.GET.get('page'))
    filter_query = request.GET.copy()
    filter_query.pop('page', None)
    return render(request, 'transaction_history.html', {
        'filter_form': filter_form,
        'filter_query': filter_query.urlencode(),
        'page_obj': page_obj,
        'transactions': page_obj.object_list,
        'today': timezone.localdate(),
    })


@login_required
def add_record(request):
    entry_forms = {
        'income': IncomeEntryForm,
        'expense': ExpenseEntryForm,
        'budget': BudgetEntryForm,
        'goal': SavingsGoalEntryForm,
    }
    selector_form = RecordTypeForm(request.POST or None)
    selected_type = request.POST.get(
        'record_type',
        request.GET.get('record_type', 'income'),
    )
    if selected_type not in entry_forms:
        selected_type = 'income'

    forms = {
        record_type: form_class(
            request.POST if request.method == 'POST' and record_type == selected_type else None,
            user=request.user,
        )
        for record_type, form_class in entry_forms.items()
    }

    if request.method == 'POST' and selector_form.is_valid():
        entry_form = forms[selected_type]
        if entry_form.is_valid():
            record = entry_form.save(commit=False)
            record.user = request.user
            record.save()
            messages.success(request, f'{selector_form.cleaned_data["record_type"].title()} saved.')
            if selected_type == 'goal':
                return redirect('savings_goals')
            return redirect('Dashboard')

    context = {
        'selector_form': selector_form,
        'entry_forms': forms,
        'selected_type': selected_type,
        'record_types': RecordTypeForm.RECORD_TYPES,
    }
    return render(request, 'record_form.html', context)


@login_required
def request_premium_upgrade(request):
    if request.method != 'POST':
        return redirect('Dashboard')

    profile, _ = Profile.objects.get_or_create(user=request.user)
    if profile.is_premium:
        messages.info(request, 'Your account already has Premium access.')
        return redirect('Dashboard')

    upgrade_request = PremiumUpgradeRequest.objects.filter(user=request.user).first()
    if upgrade_request and upgrade_request.status == PremiumUpgradeRequest.Status.PENDING:
        messages.info(request, 'You already have a Premium upgrade request awaiting review.')
        return redirect('Dashboard')

    if upgrade_request:
        upgrade_request.status = PremiumUpgradeRequest.Status.PENDING
        upgrade_request.requested_at = timezone.now()
        upgrade_request.reviewed_at = None
        upgrade_request.reviewed_by = None
        upgrade_request.save(
            update_fields=('status', 'requested_at', 'reviewed_at', 'reviewed_by'),
        )
    else:
        try:
            with transaction.atomic():
                PremiumUpgradeRequest.objects.create(user=request.user)
        except IntegrityError:
            messages.info(request, 'You already have a Premium upgrade request awaiting review.')
            return redirect('Dashboard')

    messages.success(request, 'Your Premium upgrade request was sent to an administrator.')
    return redirect('Dashboard')
