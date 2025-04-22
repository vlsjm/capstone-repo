from django.shortcuts import render, redirect
from django.views.generic import TemplateView, ListView
from .models import Supply, Property, SupplyRequest, DamageReport
from .forms import PropertyForm, SupplyForm
from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404




class DashboardPageView(TemplateView):
    template_name = 'app/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Querying supply status counts
        context['supply_available'] = Supply.objects.filter(status='available').count()
        context['supply_low_stock'] = Supply.objects.filter(status='low_stock').count()
        context['supply_out_of_stock'] = Supply.objects.filter(status='out_of_stock').count()

        # Querying property condition counts
        context['property_new'] = Property.objects.filter(condition='new').count()
        context['property_good'] = Property.objects.filter(condition='good').count()
        context['property_needs_repair'] = Property.objects.filter(condition='needs_repair').count()
        context['property_damaged'] = Property.objects.filter(condition='damaged').count()

        # General statistics
        context['supply_count'] = Supply.objects.count()
        context['property_count'] = Property.objects.count()
        context['pending_requests'] = SupplyRequest.objects.filter(status='pending').count()
        context['damage_reports'] = DamageReport.objects.filter(status='pending').count()

        # Fetch lists for tables
        context['low_stock_supplies'] = Supply.objects.filter(status='low_stock')[:10]  # Get first 10 low stock items
        context['recent_supply_requests'] = SupplyRequest.objects.order_by('-request_date')[:10]  # Get last 10 requests
        context['active_borrows'] = SupplyRequest.objects.filter(status='approved').order_by('-request_date')[:10]
        context['damage_reports_list'] = DamageReport.objects.order_by('-report_date')[:10]

        return context

class ReportPageView(TemplateView):
    template_name = 'app/reports.html'

class ActivityPageView(TemplateView):
    template_name = 'app/activity.html'

class RequestsListView(ListView):
    model = SupplyRequest
    template_name = 'app/requests.html'
    context_object_name = 'requests'

class SupplyListView(ListView):
    model = Supply
    template_name = 'app/supply.html'  # The template for listing supplies
    context_object_name = 'supplies'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = SupplyForm()  # Add the SupplyForm to the context for the modal
        return context

# Function-based view to add a new supply
def add_supply(request):
    if request.method == 'POST':
        form = SupplyForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Supply added successfully.')
        else:
            messages.error(request, 'Please correct the errors below.')
    return redirect('supply_list')  # Redirect to the supply list view after submission

class PropertyListView(ListView):
    model = Property
    template_name = 'app/property.html'  
    context_object_name = 'properties'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = PropertyForm()
        return context

def add_property(request):
    if request.method == 'POST':
        form = PropertyForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Property added successfully.')
        else:
            messages.error(request, 'Please correct the errors below.')
    return redirect('property_list')

def edit_property(request, id):
    property_obj = get_object_or_404(Property, id=id)

    if request.method == 'POST':
        # Get form values with proper validation
        property_obj.property_name = request.POST.get('property_name')
        
        # Convert quantity to integer
        quantity = request.POST.get('quantity')
        property_obj.quantity = int(quantity) if quantity else 0
        
        # Date handling
        property_obj.date_acquired = request.POST.get('date_acquired')
        property_obj.barcode = request.POST.get('barcode')
        
        # Critical fields - make sure they're not empty
        condition = request.POST.get('condition')
        if condition:  # Check if not empty
            property_obj.condition = condition
        # If empty, keep the original value - don't overwrite with None
        
        availability = request.POST.get('availability')
        if availability:  # Check if not empty
            property_obj.availability = availability
        # If empty, keep the original value - don't overwrite with None
        
        # Handle the assigned_to field - can be null
        assigned_to = request.POST.get('assigned_to')
        property_obj.assigned_to = assigned_to if assigned_to else None
        
        # Convert string 'True'/'False' to Python boolean
        available_for_request = request.POST.get('available_for_request')
        if available_for_request:
            property_obj.available_for_request = available_for_request == 'True'
        
        # Debug - print values before saving
        print(f"Saving property with condition: {property_obj.condition}")
        print(f"Saving property with availability: {property_obj.availability}")
        
        # Save the updated property
        property_obj.save()

        # Redirect after updating
        return redirect('property_list')

    # If GET request, you'd render a template, but since you're using a modal, this may not be needed
    return render(request, 'app/property_list.html', {'property': property_obj})





def delete_property(request, id):
    property = get_object_or_404(Property, id=id)
    if request.method == 'POST':
        property.delete()
        messages.success(request, 'Property deleted successfully.')
    return redirect('property_list')

class CheckOutPageView(TemplateView):
    template_name = 'app/checkout.html'

class ManageUsersPageView(TemplateView):
    template_name = 'app/manage_users.html'
