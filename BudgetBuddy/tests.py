from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class SignupViewTests(TestCase):
    def test_get_displays_signup_form(self):
        response = self.client.get(reverse('signup'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create your account')
        self.assertContains(response, 'csrfmiddlewaretoken')

    def test_valid_signup_creates_user_and_redirects_to_login(self):
        response = self.client.post(
            reverse('signup'),
            {
                'full_name': 'Taylor Example',
                'email': 'taylor@example.com',
                'password': 'SecurePass!482',
            },
        )

        user = get_user_model().objects.get(email='taylor@example.com')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('login'))
        self.assertEqual(user.first_name, 'Taylor Example')
        self.assertTrue(user.check_password('SecurePass!482'))

    def test_duplicate_email_is_rejected(self):
        user_model = get_user_model()
        user_model.objects.create_user(
            username='existing-user',
            email='taylor@example.com',
            password='AnotherPass!482',
        )

        response = self.client.post(
            reverse('signup'),
            {
                'full_name': 'Taylor Example',
                'email': 'TAYLOR@example.com',
                'password': 'SecurePass!482',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'An account with this email already exists.')
        self.assertEqual(user_model.objects.count(), 1)

    def test_weak_password_is_rejected(self):
        response = self.client.post(
            reverse('signup'),
            {
                'full_name': 'Taylor Example',
                'email': 'taylor@example.com',
                'password': '123',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This password is too short.')
        self.assertFalse(get_user_model().objects.filter(email='taylor@example.com').exists())
