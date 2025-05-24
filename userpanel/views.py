from django.views.generic import TemplateView
from django.urls import reverse_lazy
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from .forms import SupplyRequestForm, ReservationForm, DamageReportForm, BorrowForm

from django.contrib.auth.views import LoginView
from app.models import UserProfile


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


class UserLoginView(LoginView):
    template_name = 'registration/user_login.html'

    def get_success_url(self):
        return reverse_lazy('user_dashboard')  

    def form_valid(self, form):
        user = form.get_user()

        try:
            profile = UserProfile.objects.get(user=user)
            if profile.role == 'admin':
                messages.error(self.request, 'Access denied. Please use the admin login.')
                return self.form_invalid(form)
            
            if profile.role not in ['faculty', 'csg_officer']:
                messages.error(self.request, 'Access denied. Invalid user role.')
                return self.form_invalid(form)

        except UserProfile.DoesNotExist:
            messages.error(self.request, 'User profile not found.')
            return self.form_invalid(form)

        return super().form_valid(form)



class UserDashboardView(TemplateView):
    template_name = 'userpanel/user_dashboard.html'

