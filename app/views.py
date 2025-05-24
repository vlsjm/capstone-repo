from collections import defaultdict
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView, ListView

from django.views import View
from django.contrib.auth import login, authenticate
from .models import Supply, Property, BorrowRequest, SupplyRequest, DamageReport, Reservation, ActivityLog, UserProfile
from .forms import PropertyForm, SupplyForm, UserProfileForm, UserRegistrationForm
from django.contrib.auth.forms import AuthenticationForm


def create_user(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password'],
            )
            UserProfile.objects.create(
                user=user,
                role=form.cleaned_data['role'],
                department=form.cleaned_data['department'],
                phone=form.cleaned_data['phone'],
            )
            return redirect('manage_users')  # Redirect after POST
    else:
        form = UserRegistrationForm()
    # Optional: if POST failed, re-render form with errors
    users = UserProfile.objects.select_related('user').all()
    return render(request, 'app/manage_users.html', {'form': form, 'users': users})



class UserProfileListView(ListView):
    model = UserProfile
    template_name = 'app/manage_users.html'
    context_object_name = 'users'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = UserRegistrationForm()  
        return context

class DashboardPageView(TemplateView):
    template_name = 'app/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context.update({
            'supply_available': Supply.objects.filter(status__iexact='available').count(),
            'supply_low_stock': Supply.objects.filter(status__iexact='low_stock').count(),
            'supply_out_of_stock': Supply.objects.filter(status__iexact='out_of_stock').count(),

            'property_in_good_condition': Property.objects.filter(condition='In good condition').count(),
            'property_needing_repair': Property.objects.filter(condition='Needing repair').count(),
            'property_unserviceable': Property.objects.filter(condition='Unserviceable').count(),
            'property_obsolete': Property.objects.filter(condition='Obsolete').count(),
            'property_no_longer_needed': Property.objects.filter(condition='No longer needed').count(),
            'property_not_used_since_purchased': Property.objects.filter(condition='Not used since purchased').count(),

            'supply_count': Supply.objects.count(),
            'property_count': Property.objects.count(),
            'pending_requests': SupplyRequest.objects.filter(status__iexact='pending').count(),
            'damage_reports': DamageReport.objects.filter(status__iexact='pending').count(),

            'low_stock_supplies': Supply.objects.filter(status__iexact='low_stock')[:10],
            'recent_supply_requests': SupplyRequest.objects.order_by('-request_date')[:10],
            'active_borrows': SupplyRequest.objects.filter(status__iexact='approved').order_by('-request_date')[:10],
            'damage_reports_list': DamageReport.objects.order_by('-report_date')[:10],
        })

        return context


class ActivityPageView(ListView):
    model = ActivityLog
    template_name = 'app/activity.html'
    context_object_name = 'activitylog_list'
    ordering = ['-timestamp']


class UserBorrowRequestListView(ListView):
    model = BorrowRequest
    template_name = 'app/borrow.html'
    context_object_name = 'borrow_requests'

    def get_queryset(self):
        return BorrowRequest.objects.select_related('user', 'property').order_by('-borrow_date')


class UserSupplyRequestListView(ListView):
    model = SupplyRequest
    template_name = 'app/requests.html'
    context_object_name = 'requests'
    
    def get_queryset(self):
        return SupplyRequest.objects.select_related('user', 'supply').order_by('-request_date')


class UserDamageReportListView(ListView):
    model = DamageReport
    template_name = 'app/reports.html'
    context_object_name = 'damage_reports'
    
    def get_queryset(self):
        return DamageReport.objects.select_related('user', 'item').order_by('-report_date')


class UserReservationListView(ListView):
    model = Reservation
    template_name = 'app/reservation.html'
    context_object_name = 'reservations'

    def get_queryset(self):
        return Reservation.objects.select_related('user', 'item').order_by('-reservation_date')


class SupplyListView(ListView):
    model = Supply
    template_name = 'app/supply.html'
    context_object_name = 'supplies'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = SupplyForm()
        return context


def add_supply(request):
    if request.method == 'POST':
        form = SupplyForm(request.POST)
        if form.is_valid():
            supply = form.save(commit=False)
            supply._logged_in_user = request.user
            supply.save()

            ActivityLog.objects.create(
                user=request.user,
                action='create',
                model_name='Supply',
                object_repr=str(supply),
                description=f"Supply '{supply.supply_name}' was added."
            )
            messages.success(request, 'Supply added successfully.')
        else:
            messages.error(request, 'Please correct the errors below.')
    return redirect('supply_list')


@csrf_exempt
def edit_supply(request):
    if request.method == 'POST':
        supply = get_object_or_404(Supply, pk=request.POST.get('id'))
        changes = []

        def check_change(label, old, new):
            if str(old) != str(new):
                changes.append(f"{label} changed from '{old}' to '{new}'")

        check_change('Supply Name', supply.supply_name, request.POST.get('supply_name'))
        check_change('Quantity', supply.quantity, request.POST.get('quantity'))
        check_change('Date Received', supply.date_received, request.POST.get('date_received'))
        check_change('Barcode', supply.barcode, request.POST.get('barcode'))
        check_change('Category', supply.category, request.POST.get('category'))
        check_change('Status', supply.status, request.POST.get('status'))

        new_available = request.POST.get('available_for_request') == 'on'
        if supply.available_for_request != new_available:
            changes.append(f"Available For Request changed from '{supply.available_for_request}' to '{new_available}'")

        supply.supply_name = request.POST.get('supply_name')
        supply.quantity = request.POST.get('quantity')
        supply.date_received = request.POST.get('date_received')
        supply.barcode = request.POST.get('barcode')
        supply.category = request.POST.get('category')
        supply.status = request.POST.get('status')
        supply.available_for_request = new_available
        supply._logged_in_user = request.user
        supply.save()

        description = f"Supply '{supply.supply_name}' updated: " + ", ".join(changes) if changes else f"Supply '{supply.supply_name}' was updated but no changes detected."

        ActivityLog.objects.create(
            user=request.user,
            action='update',
            model_name='Supply',
            object_repr=str(supply),
            description=description
        )

        messages.success(request, 'Supply updated successfully.')
    return redirect('supply_list')


def delete_supply(request, pk):
    supply = get_object_or_404(Supply, pk=pk)
    if request.method == 'POST':
        supply_name = supply.supply_name
        repr_str = str(supply)
        supply._logged_in_user = request.user
        supply.delete()

        ActivityLog.objects.create(
            user=request.user,
            action='delete',
            model_name='Supply',
            object_repr=repr_str,
            description=f"Supply '{supply_name}' was deleted."
        )
        messages.success(request, 'Supply deleted successfully.')
    return redirect('supply_list')


class PropertyListView(ListView):
    model = Property
    template_name = 'app/property.html'
    context_object_name = 'properties'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = PropertyForm()

        grouped = defaultdict(list)
        for prop in context['properties']:
            grouped[prop.get_category_display()].append(prop)

        context['grouped_properties'] = dict(grouped)
        return context


def add_property(request):
    if request.method == 'POST':
        form = PropertyForm(request.POST)
        if form.is_valid():
            prop = form.save(commit=False)
            prop._logged_in_user = request.user
            prop.save()

            ActivityLog.objects.create(
                user=request.user,
                action='create',
                model_name='Property',
                object_repr=str(prop),
                description=f"Property '{prop.property_name}' was added."
            )

            messages.success(request, 'Property added successfully.')
        else:
            messages.error(request, f'Errors: {form.errors}')
    return redirect('property_list')


@csrf_exempt
def edit_property(request):
    if request.method == 'POST':
        prop = get_object_or_404(Property, pk=request.POST.get('id'))
        changes = []

        def check_change(label, old, new):
            if str(old) != str(new):
                changes.append(f"{label} changed from '{old}' to '{new}'")

        check_change('Property Name', prop.property_name, request.POST.get('property_name'))
        check_change('Description', prop.description, request.POST.get('description'))
        check_change('Barcode', prop.barcode, request.POST.get('barcode'))
        check_change('Unit of Measure', prop.unit_of_measure, request.POST.get('unit_of_measure'))
        check_change('Unit Value', prop.unit_value, request.POST.get('unit_value'))
        check_change('Quantity', prop.quantity, request.POST.get('quantity'))
        check_change('Location', prop.location, request.POST.get('location'))
        check_change('Condition', prop.condition, request.POST.get('condition'))
        check_change('Category', prop.category, request.POST.get('category'))

        prop.property_name = request.POST.get('property_name')
        prop.description = request.POST.get('description')
        prop.barcode = request.POST.get('barcode')
        prop.unit_of_measure = request.POST.get('unit_of_measure')
        prop.unit_value = request.POST.get('unit_value')
        prop.quantity = request.POST.get('quantity')
        prop.location = request.POST.get('location')
        prop.condition = request.POST.get('condition')
        prop.category = request.POST.get('category')
        prop._logged_in_user = request.user
        prop.save()

        description = f"Property '{prop.property_name}' updated: " + ", ".join(changes) if changes else f"Property '{prop.property_name}' was updated but no changes detected."

        ActivityLog.objects.create(
            user=request.user,
            action='update',
            model_name='Property',
            object_repr=str(prop),
            description=description
        )

        messages.success(request, 'Property updated successfully.')
    return redirect('property_list')


def delete_property(request, pk):
    prop = get_object_or_404(Property, pk=pk)
    if request.method == 'POST':
        prop_name = prop.property_name
        repr_str = str(prop)
        prop._logged_in_user = request.user
        prop.delete()

        ActivityLog.objects.create(
            user=request.user,
            action='delete',
            model_name='Property',
            object_repr=repr_str,
            description=f"Property '{prop_name}' was deleted."
        )

        messages.success(request, 'Property deleted successfully.')
    return redirect('property_list')


class CheckOutPageView(TemplateView):
    template_name = 'app/checkout.html'


class LandingPageView(TemplateView):
    template_name = "app/landing_page.html"


    
# class AdminLoginView(LoginView):
#     template_name = 'registration/admin_login.html'
#     success_url = reverse_lazy('dashboard')  
    
#     def form_valid(self, form):
#         user = form.get_user()
        
#         try:
#             profile = UserProfile.objects.get(user=user)
#             if profile.role != 'admin':
#                 messages.error(self.request, 'Access denied. Admin credentials required.')
#                 return self.form_invalid(form)
#         except UserProfile.DoesNotExist:
#             messages.error(self.request, 'Access denied. Admin credentials required.')
#             return self.form_invalid(form)
        
#         # If user is admin, proceed with normal login
#         return super().form_valid(form)

class AdminLoginView(LoginView):
    template_name = 'registration/admin_login.html'

    def get_success_url(self):
        return reverse_lazy('dashboard')

    def form_valid(self, form):
        user = form.get_user()
        try:
            profile = UserProfile.objects.get(user=user)
            if profile.role != 'admin':
                messages.error(self.request, 'Access denied. Admin credentials required.')
                return self.form_invalid(form)

        except UserProfile.DoesNotExist:
            messages.error(self.request, 'Access denied. Admin credentials required.')
            return self.form_invalid(form)

        return super().form_valid(form)
