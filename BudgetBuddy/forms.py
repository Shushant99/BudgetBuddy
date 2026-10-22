from uuid import uuid4

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password


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
