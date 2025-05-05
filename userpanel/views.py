from django.views.generic import TemplateView
from django.urls import reverse_lazy
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User




# Dashboard Page View
class UserDashboardView(TemplateView):
    template_name = 'userpanel/user_dashboard.html'

# Make a Request Page View
class UserRequestView(TemplateView):
    template_name = 'userpanel/user_request.html'

# Reserve Page View
class UserReserveView(TemplateView):
    template_name = 'userpanel/user_reserve.html'

# Report Page View
class UserReportView(TemplateView):
    template_name = 'userpanel/user_report.html'

# Custom User Login View
def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')  # Or 'email' depending on your form
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('user_dashboard')  # Redirect to the user dashboard after successful login
        else:
            messages.error(request, 'Invalid username or password.')

    return render(request, 'registration/user_login.html')

