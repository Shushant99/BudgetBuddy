from django.contrib import messages
from django.shortcuts import redirect, render

from BudgetBuddy.forms import SignupForm


def signup(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your account has been created. You can now log in.')
            return redirect('login')
    else:
        form = SignupForm()

    return render(request, 'signup.html', {'form': form})
