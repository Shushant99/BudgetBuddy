"""Reports: money in, money out and savings for any period, with filters and a CSV export."""
import csv
from datetime import date, datetime, timedelta

from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import serializers
from rest_framework.decorators import api_view
from rest_framework.response import Response

from Backend.models import Expense, Income, SavingsContribution

MAX_DAYS = 366 * 5   # longest period one report can cover
SCREEN_ROWS = 500    # transactions sent to the screen; the CSV export always has all of them


class ReportFilterSerializer(serializers.Serializer):
    from_date = serializers.DateField()
    to_date = serializers.DateField()
    record_type = serializers.ChoiceField(choices=['all', 'income', 'expense', 'savings'], default='all')
    category = serializers.ChoiceField(choices=Expense.Category.choices, required=False, allow_blank=True)

    def validate(self, data):
        if data['from_date'] > data['to_date']:
            raise serializers.ValidationError({'to_date': ['End date must be on or after the start date.']})
        if (data['to_date'] - data['from_date']).days > MAX_DAYS:
            raise serializers.ValidationError({'to_date': ['A report can cover at most 5 years.']})
        if data.get('category') and data['record_type'] in ('income', 'savings'):
            raise serializers.ValidationError({'category': ['Category only applies to expenses.']})
        return data


# ---------- dates ----------
def add_months(d, n):
    year, month = divmod(d.year * 12 + d.month - 1 + n, 12)
    return date(year, month + 1, 1)


def month_end(d):
    return add_months(d, 1) - timedelta(days=1)


def previous_period(start, end):
    """The period just before this one. Whole calendar months compare with the months before them."""
    if start.day == 1 and end == month_end(end):
        months = (end.year - start.year) * 12 + end.month - start.month + 1
        return add_months(start, -months), start - timedelta(days=1)
    days = (end - start).days + 1
    return start - timedelta(days=days), start - timedelta(days=1)


# ---------- data ----------
def scoped(user, record_type, category, start, end):
    """(income, expenses, savings) querysets for the period; the ones the filters leave out are empty."""
    def wants(kind):
        return record_type in ('all', kind) and not (category and kind != 'expense')

    income = Income.objects.filter(user=user, received_on__range=(start, end))
    expenses = Expense.objects.filter(user=user, spent_on__range=(start, end))
    savings = SavingsContribution.objects.filter(user=user, contributed_on__range=(start, end))
    if category:
        expenses = expenses.filter(category=category)
    return (
        income if wants('income') else income.none(),
        expenses if wants('expense') else expenses.none(),
        savings.select_related('goal') if wants('savings') else savings.none(),
    )


def total(qs):
    return qs.aggregate(t=Sum('amount'))['t'] or 0


def per_month(qs, field):
    rows = qs.annotate(m=TruncMonth(field)).values('m').annotate(t=Sum('amount')).order_by()
    return {(r['m'].date() if isinstance(r['m'], datetime) else r['m']): r['t'] for r in rows}


def transaction_rows(income, expenses, savings):
    """Every transaction in the three querysets, newest first."""
    rows = []
    rows += [(i.pk, {'id': f'income-{i.pk}', 'kind': 'income', 'date': i.received_on, 'category': '',
                     'description': i.source, 'amount': i.amount, 'notes': i.notes}) for i in income]
    rows += [(e.pk, {'id': f'expense-{e.pk}', 'kind': 'expense', 'date': e.spent_on,
                     'category': e.get_category_display(), 'description': e.description,
                     'amount': e.amount, 'notes': e.notes}) for e in expenses]
    rows += [(c.pk, {'id': f'savings-{c.pk}', 'kind': 'savings', 'date': c.contributed_on, 'category': '',
                     'description': c.goal.name, 'amount': c.amount, 'notes': ''}) for c in savings]
    rows.sort(key=lambda r: (r[1]['date'], r[0]), reverse=True)
    return [row for _, row in rows]


def read_filters(request):
    filters = ReportFilterSerializer(data=request.query_params)
    filters.is_valid(raise_exception=True)
    f = filters.validated_data
    return f['from_date'], f['to_date'], f['record_type'], f.get('category') or None


# ---------- views ----------
@api_view(['GET'])
def report(request):
    start, end, record_type, category = read_filters(request)
    income, expenses, savings = scoped(request.user, record_type, category, start, end)

    income_total, expense_total, savings_total = total(income), total(expenses), total(savings)

    prev_start, prev_end = previous_period(start, end)
    p_income, p_expenses, p_savings = scoped(request.user, record_type, category, prev_start, prev_end)

    by_month = []
    income_by, expense_by, savings_by = (
        per_month(income, 'received_on'), per_month(expenses, 'spent_on'), per_month(savings, 'contributed_on'),
    )
    month = start.replace(day=1)
    while month <= end:
        inc, exp, sav = income_by.get(month, 0), expense_by.get(month, 0), savings_by.get(month, 0)
        by_month.append({'month': month.strftime('%Y-%m'), 'label': month.strftime('%b %Y'),
                         'income': inc, 'expenses': exp, 'savings': sav, 'left_over': inc - exp - sav})
        month = add_months(month, 1)

    labels = dict(Expense.Category.choices)
    by_category = [
        {'category': r['category'], 'label': labels.get(r['category'], r['category']), 'amount': r['t'],
         'percent': round(float(r['t'] / expense_total * 100), 1) if expense_total else 0}
        for r in expenses.values('category').annotate(t=Sum('amount')).order_by('-t')
    ]

    rows = transaction_rows(income, expenses, savings)
    return Response({
        'period': {'from_date': start, 'to_date': end, 'days': (end - start).days + 1},
        'filters': {'record_type': record_type, 'category': category or ''},
        'totals': {'income': income_total, 'expenses': expense_total, 'savings': savings_total,
                   'left_over': income_total - expense_total - savings_total},
        'previous': {'from_date': prev_start, 'to_date': prev_end, 'income': total(p_income),
                     'expenses': total(p_expenses), 'savings': total(p_savings)},
        'by_month': by_month,
        'by_category': by_category,
        'transaction_count': len(rows),
        'transactions': rows[:SCREEN_ROWS],
        'truncated': len(rows) > SCREEN_ROWS,
        'generated_at': timezone.now().isoformat(),
    })


def safe_cell(value):
    """Stop spreadsheets from running text such as =SUM(...) that a user typed into a description."""
    text = str(value)
    return "'" + text if text[:1] in ('=', '+', '-', '@', '\t', '\r') else text


@api_view(['GET'])
def report_export(request):
    start, end, record_type, category = read_filters(request)
    rows = transaction_rows(*scoped(request.user, record_type, category, start, end))

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="budget-buddy-report_{start}_to_{end}.csv"'
    response.write('\ufeff')  # lets Excel open it as UTF-8
    out = csv.writer(response)
    out.writerow(['Date', 'Type', 'Category', 'Description', 'Amount', 'Notes'])
    for r in rows:
        out.writerow([r['date'].isoformat(), r['kind'].capitalize(), r['category'],
                      safe_cell(r['description']), f"{r['amount']:.2f}", safe_cell(r['notes'])])
    return response