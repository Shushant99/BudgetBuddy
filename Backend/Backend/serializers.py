from decimal import Decimal
from uuid import uuid4

from django.contrib.auth import authenticate, get_user_model, password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from Backend.models import Budget, Expense, Income, Profile, SavingsGoal

User = get_user_model()


class SignupSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=150)
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_email(self, value):
        value = value.lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('An account with this email already exists.')
        return value

    def validate(self, data):
        user = User(email=data['email'], first_name=data['full_name'])
        try:
            password_validation.validate_password(data['password'], user)
        except DjangoValidationError as e:
            raise serializers.ValidationError({'password': list(e.messages)})
        return data

    def create(self, data):
        user = User.objects.create_user(
            username=uuid4().hex,
            email=data['email'],
            first_name=data['full_name'],
            password=data['password'],
        )
        Profile.objects.create(user=user)
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(trim_whitespace=False)

    def validate(self, data):
        found = User.objects.filter(email__iexact=data['email']).first()
        username = found.get_username() if found else data['email']
        user = authenticate(username=username, password=data['password'])
        if user is None:
            raise serializers.ValidationError('Invalid email or password.')
        data['user'] = user
        return data


class IncomeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Income
        fields = ('source', 'amount', 'received_on', 'notes')


class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = ('category', 'description', 'amount', 'spent_on', 'notes')


class BudgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Budget
        fields = ('category', 'amount', 'start_date', 'end_date')

    def validate(self, data):
        if data['end_date'] < data['start_date']:
            raise serializers.ValidationError('End date must be on or after the start date.')
        if Budget.objects.filter(
            user=self.context['request'].user,
            category=data['category'],
            start_date=data['start_date'],
            end_date=data['end_date'],
        ).exists():
            raise serializers.ValidationError('You already have a budget for this category and date range.')
        return data


class SavingsGoalSerializer(serializers.ModelSerializer):
    remaining_amount = serializers.SerializerMethodField()
    percent = serializers.SerializerMethodField()

    class Meta:
        model = SavingsGoal
        fields = ('id', 'name', 'target_amount', 'current_amount', 'target_date',
                  'status', 'remaining_amount', 'percent')
        read_only_fields = ('id', 'status')

    def get_remaining_amount(self, obj):
        return obj.target_amount - obj.current_amount

    def get_percent(self, obj):
        return min(round(float(obj.current_amount / obj.target_amount * 100)), 100)

    def validate(self, data):
        if data.get('current_amount', 0) > data['target_amount']:
            raise serializers.ValidationError('Current amount cannot exceed the target amount.')
        return data


class ContributionSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('0.01'))


class TransactionFilterSerializer(serializers.Serializer):
    record_type = serializers.ChoiceField(choices=['all', 'income', 'expense', 'savings'], default='all')
    from_date = serializers.DateField(required=False)
    to_date = serializers.DateField(required=False)

    def validate(self, data):
        if data.get('from_date') and data.get('to_date') and data['from_date'] > data['to_date']:
            raise serializers.ValidationError({'to_date': ['End date must be on or after the start date.']})
        return data