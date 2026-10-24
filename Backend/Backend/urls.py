"""
URL configuration for Backend project.

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
from django.urls import path

from Backend import api_views as v

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/signup/', v.signup),
    path('api/login/', v.login_view),
    path('api/logout/', v.logout_view),
    path('api/dashboard/', v.dashboard),
    path('api/transactions/', v.transactions),
    path('api/records/', v.add_record),
    path('api/savings-goals/', v.savings_goals),
    path('api/savings-goals/<int:goal_id>/contribute/', v.contribute),
    path('api/premium-request/', v.request_premium),
]