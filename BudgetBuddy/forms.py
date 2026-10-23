from uuid import uuid4

from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone

from BudgetBuddy.models import Budget, Expense, Income, SavingsGoal


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label='Email address',
        widget=forms.EmailInput(attrs={
            'autofocus': True,
            'autocomplete': 'email',
            'placeholder': 'you@example.com',
        }),
    )

    def clean(self):
        email = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        if email and password:
            user_model = get_user_model()
            user = user_model.objects.filter(email__iexact=email).first()
            username = user.get_username() if user else email
            self.user_cache = authenticate(
                self.request,
                username=username,
                password=password,
            )
            if self.user_cache is None:
                raise self.get_invalid_login_error()
            self.confirm_login_allowed(self.user_cache)
        return self.cleaned_data


class SignupForm(forms.Form):
    full_name = forms.CharField(max_length=150)
    email = forms.EmailField(max_length=254)
    password = forms.CharField(strip=False, widget=forms.PasswordInput)

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        user_model = get_user_model()
        if user_model.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def clean_password(self):
        password = self.cleaned_data['password']
        user_model = get_user_model()
        user = user_model(
            email=self.cleaned_data.get('email', ''),
            first_name=self.cleaned_data.get('full_name', ''),
        )
        validate_password(password, user)
        return password

    def save(self):
        user_model = get_user_model()
        return user_model.objects.create_user(
            username=uuid4().hex,
            email=self.cleaned_data['email'],
            first_name=self.cleaned_data['full_name'],
            password=self.cleaned_data['password'],
        )


class RecordTypeForm(forms.Form):
    RECORD_TYPES = (
        ('income', 'Income'),
        ('expense', 'Expense'),
        ('budget', 'Budget'),
        ('goal', 'Savings goal'),
    )
    record_type = forms.ChoiceField(
        choices=RECORD_TYPES,
        label='What would you like to add?',
    )


class TransactionFilterForm(forms.Form):
    RECORD_TYPES = (
        ('all', 'All transactions'),
        ('income', 'Income'),
        ('expense', 'Expenses'),
        ('savings', 'Savings contributions'),
    )
    record_type = forms.ChoiceField(
        choices=RECORD_TYPES,
        required=False,
        initial='all',
        label='Type',
    )
    from_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='From',
    )
    to_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='To',
    )

    def clean(self):
        cleaned_data = super().clean()
        from_date = cleaned_data.get('from_date')
        to_date = cleaned_data.get('to_date')
        if from_date and to_date and from_date > to_date:
            self.add_error('to_date', 'End date must be on or after the start date.')
        return cleaned_data


class UserEntryFormMixin:
    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        if not self.is_bound:
            for field_name in ('received_on', 'spent_on'):
                if field_name in self.fields:
                    self.fields[field_name].initial = timezone.localdate()

    date_widgets = {
        'received_on': forms.DateInput(attrs={'type': 'date'}),
        'spent_on': forms.DateInput(attrs={'type': 'date'}),
        'start_date': forms.DateInput(attrs={'type': 'date'}),
        'end_date': forms.DateInput(attrs={'type': 'date'}),
        'target_date': forms.DateInput(attrs={'type': 'date'}),
    }


class IncomeEntryForm(UserEntryFormMixin, forms.ModelForm):
    class Meta:
        model = Income
        fields = ('source', 'amount', 'received_on', 'notes')
        widgets = {
            **UserEntryFormMixin.date_widgets,
            'notes': forms.Textarea(attrs={'rows': 3}),
        }


class ExpenseEntryForm(UserEntryFormMixin, forms.ModelForm):
    class Meta:
        model = Expense
        fields = ('category', 'description', 'amount', 'spent_on', 'notes')
        widgets = {
            **UserEntryFormMixin.date_widgets,
            'notes': forms.Textarea(attrs={'rows': 3}),
        }


class BudgetEntryForm(UserEntryFormMixin, forms.ModelForm):
    class Meta:
        model = Budget
        fields = ('category', 'amount', 'start_date', 'end_date')
        widgets = UserEntryFormMixin.date_widgets

    def clean(self):
        cleaned_data = super().clean()
        if self.user and all(
            cleaned_data.get(field)
            for field in ('category', 'start_date', 'end_date')
        ) and Budget.objects.filter(
            user=self.user,
            category=cleaned_data['category'],
            start_date=cleaned_data['start_date'],
            end_date=cleaned_data['end_date'],
        ).exists():
            raise forms.ValidationError(
                'You already have a budget for this category and date range.'
            )
        return cleaned_data


class SavingsGoalEntryForm(UserEntryFormMixin, forms.ModelForm):
    class Meta:
        model = SavingsGoal
        fields = ('name', 'target_amount', 'current_amount', 'target_date')
        widgets = UserEntryFormMixin.date_widgets


class SavingsContributionForm(forms.Form):
    amount = forms.DecimalField(
        min_value=0.01,
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'min': '0.01',
            'step': '0.01',
            'placeholder': 'Amount',
            'aria-label': 'Contribution amount in rupees',
        }),
        label='Add to savings',
    )
