from django.views.generic import TemplateView
from django.urls import reverse_lazy
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from .forms import SupplyRequestForm, ReservationForm, DamageReportForm, BorrowForm


class UserBorrowView( TemplateView):
    template_name = 'userpanel/user_borrow.html'

    def get(self, request):
        form = BorrowForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = BorrowForm(request.POST)
        if form.is_valid():
            borrow_request = form.save(commit=False)
            borrow_request.user = request.user
            borrow_request.status = 'approved'  # default status
            borrow_request.save()
            messages.success(request, 'Borrow request submitted successfully.')
            return redirect('user_borrow')
        return render(request, self.template_name, {'form': form})


class UserRequestView(TemplateView):
    template_name = 'userpanel/user_request.html'

    def get(self, request):
        form = SupplyRequestForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = SupplyRequestForm(request.POST)
        if form.is_valid():
            supply_request = form.save(commit=False)
            supply_request.user = request.user
            supply_request.save()
            messages.success(request, 'Supply request submitted successfully.')
            return redirect('user_request')
        return render(request, self.template_name, {'form': form})


class UserReserveView(TemplateView):
    template_name = 'userpanel/user_reserve.html'

    def get(self, request):
        form = ReservationForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = ReservationForm(request.POST)
        if form.is_valid():
            reservation = form.save(commit=False)
            reservation.user = request.user
            reservation.save()
            messages.success(request, 'Reservation submitted successfully.')
            return redirect('user_reserve')
        return render(request, self.template_name, {'form': form})


class UserReportView(TemplateView):
    template_name = 'userpanel/user_report.html'

    def get(self, request):
        form = DamageReportForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = DamageReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.user = request.user
            report.save()
            messages.success(request, 'Damage report submitted successfully.')
            return redirect('user_report')
        return render(request, self.template_name, {'form': form})


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

# Dashboard Page View
class UserDashboardView(TemplateView):
    template_name = 'userpanel/user_dashboard.html'

