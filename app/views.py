from django.shortcuts import render
from django.views.generic import TemplateView, ListView
from .models import Supply

class DashboardPageView(TemplateView):
    template_name = 'app/dashboard.html'

class InventoryPageView(TemplateView):
    template_name = 'app/inventory.html'

class RequestsPageView(TemplateView):
    template_name = 'app/requests.html'

class ReportPageView(TemplateView):
    template_name = 'app/reports.html'

class SettingsPageView(TemplateView):
    template_name = 'app/settings.html'

class SupplyListView(ListView):
    model = Supply
    template_name = 'app/supply.html'  
    context_object_name = 'supplies'  

