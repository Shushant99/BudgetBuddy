"""
URL configuration for BudgetBuddy project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path
from django.views.generic import TemplateView

from BudgetBuddy.forms import EmailAuthenticationForm
from BudgetBuddy.views import (
    add_record,
    contribute_to_savings_goal,
    dashboard,
    request_premium_upgrade,
    savings_goals,
    signup,
    transaction_history,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name='index.html'), name='home'),
    path(
        'login/',
        auth_views.LoginView.as_view(
            template_name='login.html',
            authentication_form=EmailAuthenticationForm,
            redirect_authenticated_user=True,
            next_page='Dashboard',
        ),
        name='login',
    ),
    path(
        'logout/',
        auth_views.LogoutView.as_view(next_page='home'),
        name='logout',
    ),
    path('signup/', signup, name='signup'),
    path('Dashboard/', dashboard, name='Dashboard'),
    path('Dashboard/savings-goals/', savings_goals, name='savings_goals'),
    path(
        'Dashboard/goals/<int:goal_id>/contribute/',
        contribute_to_savings_goal,
        name='contribute_to_savings_goal',
    ),
    path('Dashboard/transactions/', transaction_history, name='transaction_history'),
    path('Dashboard/add-record/', add_record, name='add_record'),
    path('Dashboard/request-premium/', request_premium_upgrade, name='request_premium_upgrade'),
]
