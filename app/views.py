from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView, ListView
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from collections import defaultdict
from django.urls import reverse_lazy  # ✅ Add this line
from django.contrib.auth.views import LoginView
from .models import Supply, Property, SupplyRequest, DamageReport, ActivityLog, UserProfile
from .forms import PropertyForm, SupplyForm, UserProfileForm
  # If you have a form for adding/editing profiles

class UserProfileListView(ListView):
    model = UserProfile
    template_name = 'app/manage_users.html'
    context_object_name = 'profiles'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = UserProfileForm()  # Optional, if you're using a modal form or similar

        grouped = defaultdict(list)
        for profile in context['profiles']:
            role_name = profile.get_role_display()  # human-readable role from choices
            grouped[role_name].append(profile)

        context['grouped_profiles'] = dict(grouped)
        return context

#ITOOOOOOOOOOO HAAA!!!!

class DashboardPageView(TemplateView):
    template_name = 'app/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Supply status counts
        context['supply_available'] = Supply.objects.filter(status__iexact='available').count()
        context['supply_low_stock'] = Supply.objects.filter(status__iexact='low_stock').count()
        context['supply_out_of_stock'] = Supply.objects.filter(status__iexact='out_of_stock').count()

        # Property condition counts
        context['property_in_good_condition'] = Property.objects.filter(condition='In good condition').count()
        context['property_needing_repair'] = Property.objects.filter(condition='Needing repair').count()
        context['property_unserviceable'] = Property.objects.filter(condition='Unserviceable').count()
        context['property_obsolete'] = Property.objects.filter(condition='Obsolete').count()
        context['property_no_longer_needed'] = Property.objects.filter(condition='No longer needed').count()
        context['property_not_used_since_purchased'] = Property.objects.filter(condition='Not used since purchased').count()

        # General statistics
        context['supply_count'] = Supply.objects.count()
        context['property_count'] = Property.objects.count()
        context['pending_requests'] = SupplyRequest.objects.filter(status__iexact='pending').count()
        context['damage_reports'] = DamageReport.objects.filter(status__iexact='pending').count()

        # Lists for tables
        context['low_stock_supplies'] = Supply.objects.filter(status__iexact='low_stock')[:10]
        context['recent_supply_requests'] = SupplyRequest.objects.order_by('-request_date')[:10]
        context['active_borrows'] = SupplyRequest.objects.filter(status__iexact='approved').order_by('-request_date')[:10]
        context['damage_reports_list'] = DamageReport.objects.order_by('-report_date')[:10]

        return context


class ActivityPageView(ListView):
    model = ActivityLog
    template_name = 'app/activity.html'
    context_object_name = 'activitylog_list'
    ordering = ['-timestamp']  # Order newest first


class ReportPageView(TemplateView):
    template_name = 'app/reports.html'


class RequestsListView(ListView):
    model = SupplyRequest
    template_name = 'app/requests.html'
    context_object_name = 'requests'


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

        def check_change(field_label, old, new):
            if str(old) != str(new):
                changes.append(f"{field_label} changed from '{old}' to '{new}'")

        check_change('Supply Name', supply.supply_name, request.POST.get('supply_name'))
        check_change('Quantity', supply.quantity, request.POST.get('quantity'))
        check_change('Date Received', supply.date_received, request.POST.get('date_received'))
        check_change('Barcode', supply.barcode, request.POST.get('barcode'))
        check_change('Category', supply.category, request.POST.get('category'))
        check_change('Status', supply.status, request.POST.get('status'))

        old_available = supply.available_for_request
        new_available = request.POST.get('available_for_request') == 'on'
        if old_available != new_available:
            changes.append(f"Available For Request changed from '{old_available}' to '{new_available}'")

        # Update the supply fields
        supply.supply_name = request.POST.get('supply_name')
        supply.quantity = request.POST.get('quantity')
        supply.date_received = request.POST.get('date_received')
        supply.barcode = request.POST.get('barcode')
        supply.category = request.POST.get('category')
        supply.status = request.POST.get('status')
        supply.available_for_request = new_available
        supply._logged_in_user = request.user
        supply.save()

        if changes:
            description = f"Supply '{supply.supply_name}' updated: " + ", ".join(changes) + "."
        else:
            description = f"Supply '{supply.supply_name}' was updated but no changes detected."

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
        repr_str = str(supply)
        supply_name = supply.supply_name
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
            category_name = prop.get_category_display()
            grouped[category_name].append(prop)

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
            # You could print or log form.errors here for debugging

        return redirect('property_list')
    else:
        messages.error(request, 'Invalid request method.')
        return redirect('property_list')


@csrf_exempt
def edit_property(request):
    if request.method == 'POST':
        prop = get_object_or_404(Property, pk=request.POST.get('id'))

        changes = []

        def check_change(field_label, old, new):
            if str(old) != str(new):
                changes.append(f"{field_label} changed from '{old}' to '{new}'")

        check_change('Property Name', prop.property_name, request.POST.get('property_name'))
        check_change('Description', prop.description, request.POST.get('description'))
        check_change('Barcode', prop.barcode, request.POST.get('barcode'))
        check_change('Unit of Measure', prop.unit_of_measure, request.POST.get('unit_of_measure'))
        check_change('Unit Value', prop.unit_value, request.POST.get('unit_value'))
        check_change('Quantity', prop.quantity, request.POST.get('quantity'))
        check_change('Location', prop.location, request.POST.get('location'))
        check_change('Condition', prop.condition, request.POST.get('condition'))
        check_change('Category', prop.category, request.POST.get('category'))

        # Update the property fields
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

        if changes:
            description = f"Property '{prop.property_name}' updated: " + ", ".join(changes) + "."
        else:
            description = f"Property '{prop.property_name}' was updated but no changes detected."

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
    property_obj = get_object_or_404(Property, pk=pk)
    if request.method == 'POST':
        repr_str = str(property_obj)
        property_name = property_obj.property_name
        property_obj._logged_in_user = request.user
        property_obj.delete()

        ActivityLog.objects.create(
            user=request.user,
            action='delete',
            model_name='Property',
            object_repr=repr_str,
            description=f"Property '{property_name}' was deleted."
        )

        messages.success(request, 'Property deleted successfully.')
    return redirect('property_list')


class CheckOutPageView(TemplateView):
    template_name = 'app/checkout.html'




def manage_users_view(request):
    users = UserProfile.objects.select_related('user').all()
    admins = users.filter(role='admin')
    faculty = users.filter(role='faculty')
    csg_officers = users.filter(role='csg_officer')

    # Assuming you have a user creation form instance
    form = YourUserCreationForm()  

    context = {
        'admins': admins,
        'faculty': faculty,
        'csg_officers': csg_officers,
        'form': form,
    }
    return render(request, 'app/manage_users.html', context)



class DashboardPageView(TemplateView):
    template_name = 'app/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Supply status counts
        context['supply_available'] = Supply.objects.filter(status__iexact='available').count()
        context['supply_low_stock'] = Supply.objects.filter(status__iexact='low_stock').count()
        context['supply_out_of_stock'] = Supply.objects.filter(status__iexact='out_of_stock').count()

        # Property condition counts
        context['property_in_good_condition'] = Property.objects.filter(condition='In good condition').count()
        context['property_needing_repair'] = Property.objects.filter(condition='Needing repair').count()
        context['property_unserviceable'] = Property.objects.filter(condition='Unserviceable').count()
        context['property_obsolete'] = Property.objects.filter(condition='Obsolete').count()
        context['property_no_longer_needed'] = Property.objects.filter(condition='No longer needed').count()
        context['property_not_used_since_purchased'] = Property.objects.filter(condition='Not used since purchased').count()

        # General statistics
        context['supply_count'] = Supply.objects.count()
        context['property_count'] = Property.objects.count()
        context['pending_requests'] = SupplyRequest.objects.filter(status__iexact='pending').count()
        context['damage_reports'] = DamageReport.objects.filter(status__iexact='pending').count()

        # Lists for tables
        context['low_stock_supplies'] = Supply.objects.filter(status__iexact='low_stock')[:10]
        context['recent_supply_requests'] = SupplyRequest.objects.order_by('-request_date')[:10]
        context['active_borrows'] = SupplyRequest.objects.filter(status__iexact='approved').order_by('-request_date')[:10]
        context['damage_reports_list'] = DamageReport.objects.order_by('-report_date')[:10]

        return context


class ActivityPageView(ListView):
    model = ActivityLog
    template_name = 'app/activity.html'
    context_object_name = 'activitylog_list'
    ordering = ['-timestamp']  # Order newest first


class ReportPageView(TemplateView):
    template_name = 'app/reports.html'


class RequestsListView(ListView):
    model = SupplyRequest
    template_name = 'app/requests.html'
    context_object_name = 'requests'


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

        def check_change(field_label, old, new):
            if str(old) != str(new):
                changes.append(f"{field_label} changed from '{old}' to '{new}'")

        check_change('Supply Name', supply.supply_name, request.POST.get('supply_name'))
        check_change('Quantity', supply.quantity, request.POST.get('quantity'))
        check_change('Date Received', supply.date_received, request.POST.get('date_received'))
        check_change('Barcode', supply.barcode, request.POST.get('barcode'))
        check_change('Category', supply.category, request.POST.get('category'))
        check_change('Status', supply.status, request.POST.get('status'))

        old_available = supply.available_for_request
        new_available = request.POST.get('available_for_request') == 'on'
        if old_available != new_available:
            changes.append(f"Available For Request changed from '{old_available}' to '{new_available}'")

        # Update the supply fields
        supply.supply_name = request.POST.get('supply_name')
        supply.quantity = request.POST.get('quantity')
        supply.date_received = request.POST.get('date_received')
        supply.barcode = request.POST.get('barcode')
        supply.category = request.POST.get('category')
        supply.status = request.POST.get('status')
        supply.available_for_request = new_available
        supply._logged_in_user = request.user
        supply.save()

        if changes:
            description = f"Supply '{supply.supply_name}' updated: " + ", ".join(changes) + "."
        else:
            description = f"Supply '{supply.supply_name}' was updated but no changes detected."

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
        repr_str = str(supply)
        supply_name = supply.supply_name
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
            category_name = prop.get_category_display()
            grouped[category_name].append(prop)

        context['grouped_properties'] = dict(grouped)
        return context

class LandingPageView(TemplateView):
    template_name = "app/landing_page.html"


class AdminLoginView(LoginView):
    template_name = 'registration/admin_login.html'

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
            # You could print or log form.errors here for debugging

        return redirect('property_list')
    else:
        messages.error(request, 'Invalid request method.')
        return redirect('property_list')


@csrf_exempt
def edit_property(request):
    if request.method == 'POST':
        prop = get_object_or_404(Property, pk=request.POST.get('id'))

        changes = []

        def check_change(field_label, old, new):
            if str(old) != str(new):
                changes.append(f"{field_label} changed from '{old}' to '{new}'")

        check_change('Property Name', prop.property_name, request.POST.get('property_name'))
        check_change('Description', prop.description, request.POST.get('description'))
        check_change('Barcode', prop.barcode, request.POST.get('barcode'))
        check_change('Unit of Measure', prop.unit_of_measure, request.POST.get('unit_of_measure'))
        check_change('Unit Value', prop.unit_value, request.POST.get('unit_value'))
        check_change('Quantity', prop.quantity, request.POST.get('quantity'))
        check_change('Location', prop.location, request.POST.get('location'))
        check_change('Condition', prop.condition, request.POST.get('condition'))
        check_change('Category', prop.category, request.POST.get('category'))

        # Update the property fields
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

        if changes:
            description = f"Property '{prop.property_name}' updated: " + ", ".join(changes) + "."
        else:
            description = f"Property '{prop.property_name}' was updated but no changes detected."

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
    property_obj = get_object_or_404(Property, pk=pk)
    if request.method == 'POST':
        repr_str = str(property_obj)
        property_name = property_obj.property_name
        property_obj._logged_in_user = request.user
        property_obj.delete()

        ActivityLog.objects.create(
            user=request.user,
            action='delete',
            model_name='Property',
            object_repr=repr_str,
            description=f"Property '{property_name}' was deleted."
        )

        messages.success(request, 'Property deleted successfully.')
    return redirect('property_list')


class CheckOutPageView(TemplateView):
    template_name = 'app/checkout.html'