from django.shortcuts import render
from django.views.generic import TemplateView

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
