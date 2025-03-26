from django.shortcuts import render
from django.views.generic import TemplateView, ListView
from .models import Supply, Property, SupplyRequest


class DashboardPageView(TemplateView):
    template_name = 'app/dashboard.html'

class ReportPageView(TemplateView):
    template_name = 'app/reports.html'

class ActivityPageView(TemplateView):
    template_name = 'app/activity.html'

class RequestsListView(ListView):
    model = SupplyRequest
    template_name = 'app/requests.html'
    context_object_name ='requests'

class SupplyListView(ListView):
    model = Supply
    template_name = 'app/supply.html'  
    context_object_name = 'supplies'  

class PropertyListView(ListView):
    model = Property
    template_name = 'app/property.html'  
    context_object_name = 'properties'

class CheckOutPageView(TemplateView):
    template_name = 'app/checkout.html'

class ManageUsersPageView(TemplateView):
    template_name = 'app/manage_users.html'