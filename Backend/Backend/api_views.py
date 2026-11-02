from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import F, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from Backend.models import (
    Budget, Expense, Income, PremiumUpgradeRequest, Profile, SavingsContribution, SavingsGoal,
)
from Backend.serializers import (
    BudgetSerializer, ContributionSerializer, ExpenseSerializer, IncomeSerializer, LoginSerializer,
    SavingsGoalSerializer, SignupSerializer, TransactionFilterSerializer,
)


def user_payload(user):
    return {'id': user.id, 'name': user.first_name or 'there', 'email': user.email, 'is_staff': user.is_staff}


# ---------- auth ----------
@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def signup(request):
    serializer = SignupSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    token, _ = Token.objects.get_or_create(user=user)
    return Response({'token': token.key, 'user': user_payload(user)}, status=201)


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.validated_data['user']
    token, _ = Token.objects.get_or_create(user=user)
    return Response({'token': token.key, 'user': user_payload(user)})


@api_view(['POST'])
def logout_view(request):
    Token.objects.filter(user=request.user).delete()
    return Response(status=204)


# ---------- shared helper ----------
def collect_transactions(user, record_type='all', from_date=None, to_date=None, limit=None):
    def narrow(qs, field):
        if from_date:
            qs = qs.filter(**{f'{field}__gte': from_date})
        if to_date:
            qs = qs.filter(**{f'{field}__lte': to_date})
        return qs[:limit] if limit else qs

    items = []
    if record_type in ('all', 'income'):
        items += [
            {'id': f'income-{i.id}', 'title': i.source, 'detail': 'Income',
             'date': i.received_on, 'amount': i.amount, 'kind': 'income'}
            for i in narrow(Income.objects.filter(user=user), 'received_on')
        ]
    if record_type in ('all', 'expense'):
        items += [
            {'id': f'expense-{e.id}', 'title': e.description or e.get_category_display(),
             'detail': e.get_category_display(), 'date': e.spent_on, 'amount': e.amount, 'kind': 'expense'}
            for e in narrow(Expense.objects.filter(user=user), 'spent_on')
        ]
    if record_type in ('all', 'savings'):
        items += [
            {'id': f'savings-{c.id}', 'title': c.goal.name, 'detail': 'Savings contribution',
             'date': c.contributed_on, 'amount': c.amount, 'kind': 'savings'}
            for c in narrow(SavingsContribution.objects.filter(user=user).select_related('goal'), 'contributed_on')
        ]
    items.sort(key=lambda t: t['date'], reverse=True)
    return items[:limit] if limit else items

# ---------- dashboard ----------
def net_before(user, day):
    """Income minus expenses minus savings contributions dated before `day`.

    This is the money left over from earlier months, which carries into the current month.
    """
    def total(model, field):
        return model.objects.filter(user=user, **{f'{field}__lt': day}).aggregate(t=Sum('amount'))['t'] or 0

    return total(Income, 'received_on') - total(Expense, 'spent_on') - total(SavingsContribution, 'contributed_on')


@api_view(['GET'])
def dashboard(request):
    user = request.user
    today = timezone.localdate()
    month_start = today.replace(day=1)
    profile, _ = Profile.objects.get_or_create(user=user)

    expenses = Expense.objects.filter(user=user, spent_on__gte=month_start, spent_on__lte=today)
    monthly_expenses = expenses.aggregate(t=Sum('amount'))['t'] or 0
    monthly_income = Income.objects.filter(
        user=user, received_on__gte=month_start, received_on__lte=today,
    ).aggregate(t=Sum('amount'))['t'] or 0
    monthly_savings = SavingsContribution.objects.filter(
        user=user, contributed_on__gte=month_start, contributed_on__lte=today,
    ).aggregate(t=Sum('amount'))['t'] or 0

    # Leftover from earlier months carries forward; savings already moved into goals stay in the goals.
    carried_over = net_before(user, month_start)
    total_saved = SavingsGoal.objects.filter(user=user).aggregate(t=Sum('current_amount'))['t'] or 0

    budget_rows = []
    for b in Budget.objects.filter(user=user, start_date__lte=today, end_date__gte=today):
        spent = Expense.objects.filter(
            user=user, category=b.category, spent_on__gte=b.start_date, spent_on__lte=today,
        ).aggregate(t=Sum('amount'))['t'] or 0
        budget_rows.append({
            'id': b.id, 'category': b.get_category_display(), 'amount': b.amount,
            'spent': spent, 'percent': min(round(float(spent / b.amount * 100)), 100),
        })

    # Totals across ALL active budgets (the `budgets` list below is trimmed to 4 for display).
    budget_spent = sum((r['spent'] for r in budget_rows), 0)
    budgets_over = sum(1 for r in budget_rows if r['spent'] > r['amount'])

    # Where the money goes: everything available this month, split into spent / saved / reserved / free.
    reserved = {}
    for r in budget_rows:
        left = r['amount'] - r['spent']
        if left > 0:
            reserved[r['category']] = reserved.get(r['category'], 0) + left
    available = carried_over + monthly_income
    allocation = {
        'available': available,
        'spent': monthly_expenses,
        'saved': monthly_savings,
        'reserved': [{'label': k, 'amount': v} for k, v in sorted(reserved.items(), key=lambda kv: -kv[1])],
        'free': available - monthly_expenses - monthly_savings - sum(reserved.values(), 0),
    }

    category_spending = []
    if profile.is_premium:
        labels = dict(Expense.Category.choices)
        totals = list(expenses.values('category').annotate(total=Sum('amount')).order_by('-total')[:4])
        top = totals[0]['total'] if totals else 0
        category_spending = [
            {'label': labels[r['category']], 'amount': r['total'],
             'percent': round(float(r['total'] / top * 100)) if top else 0}
            for r in totals
        ]

    upgrade = PremiumUpgradeRequest.objects.filter(user=user).first()
    goals = SavingsGoal.objects.filter(user=user, status=SavingsGoal.Status.ACTIVE)[:3]

    return Response({
        'first_name': user.first_name,
        'is_premium': profile.is_premium,
        'upgrade_status': upgrade.status if upgrade else None,
        'monthly_income': monthly_income,
        'monthly_expenses': monthly_expenses,
        'monthly_savings': monthly_savings,
        'carried_over': carried_over,
        'monthly_balance': carried_over + monthly_income - monthly_expenses - monthly_savings,
        'total_saved': total_saved,
        'budget_total': sum((r['amount'] for r in budget_rows), 0),
        'budget_spent': budget_spent,
        'budgets_over': budgets_over,
        'allocation': allocation,
        'budgets': budget_rows[:4],
        'goals': SavingsGoalSerializer(goals, many=True).data,
        'transactions': collect_transactions(user, limit=10),
        'category_spending': category_spending,
    })

# ---------- transactions ----------
@api_view(['GET'])
def transactions(request):
    filters = TransactionFilterSerializer(data=request.query_params)
    filters.is_valid(raise_exception=True)
    f = filters.validated_data
    items = collect_transactions(request.user, f['record_type'], f.get('from_date'), f.get('to_date'))
    page = Paginator(items, 25).get_page(request.query_params.get('page'))
    return Response({
        'count': page.paginator.count,
        'page': page.number,
        'num_pages': page.paginator.num_pages,
        'results': list(page.object_list),
    })


# ---------- add record ----------
RECORD_SERIALIZERS = {
    'income': IncomeSerializer,
    'expense': ExpenseSerializer,
    'budget': BudgetSerializer,
    'goal': SavingsGoalSerializer,
}


@api_view(['POST'])
def add_record(request):
    serializer_class = RECORD_SERIALIZERS.get(request.data.get('record_type'))
    if serializer_class is None:
        return Response({'record_type': ['Choose a valid record type.']}, status=400)
    serializer = serializer_class(data=request.data, context={'request': request})
    serializer.is_valid(raise_exception=True)
    serializer.save(user=request.user)
    return Response(serializer.data, status=201)


# ---------- savings goals ----------
@api_view(['GET'])
def savings_goals(request):
    goals = SavingsGoal.objects.filter(user=request.user)
    return Response(SavingsGoalSerializer(goals, many=True).data)


@api_view(['POST'])
def contribute(request, goal_id):
    serializer = ContributionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    amount = serializer.validated_data['amount']

    with transaction.atomic():
        goal = get_object_or_404(
            SavingsGoal.objects.select_for_update(),
            pk=goal_id, user=request.user, status=SavingsGoal.Status.ACTIVE,
        )
        remaining = goal.target_amount - goal.current_amount
        if amount > remaining:
            return Response({'amount': [f'Cannot exceed the remaining ₹{remaining:.2f}.']}, status=400)

        SavingsContribution.objects.create(
            user=request.user, goal=goal, amount=amount, contributed_on=timezone.localdate(),
        )
        goal.current_amount = F('current_amount') + amount
        fields = ['current_amount', 'updated_at']
        if amount == remaining:
            goal.status = SavingsGoal.Status.COMPLETED
            fields.append('status')
        goal.save(update_fields=fields)

    return Response({'detail': f'₹{amount:.2f} added to {goal.name}.'})


# ---------- premium ----------
@api_view(['POST'])
def request_premium(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if profile.is_premium:
        return Response({'detail': 'Your account already has Premium access.'})

    pending_msg = 'You already have a Premium upgrade request awaiting review.'
    existing = PremiumUpgradeRequest.objects.filter(user=request.user).first()
    if existing and existing.status == PremiumUpgradeRequest.Status.PENDING:
        return Response({'detail': pending_msg})

    if existing:
        existing.status = PremiumUpgradeRequest.Status.PENDING
        existing.requested_at = timezone.now()
        existing.reviewed_at = None
        existing.reviewed_by = None
        existing.save(update_fields=('status', 'requested_at', 'reviewed_at', 'reviewed_by'))
    else:
        try:
            with transaction.atomic():
                PremiumUpgradeRequest.objects.create(user=request.user)
        except IntegrityError:
            return Response({'detail': pending_msg})

    return Response({'detail': 'Your Premium upgrade request was sent to an administrator.'}, status=201)