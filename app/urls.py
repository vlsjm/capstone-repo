from django.urls import path
from .views import (
    DashboardPageView,
    InventoryPageView,
    RequestsPageView,
    ReportPageView,
    SettingsPageView
)

urlpatterns = [
    path('', DashboardPageView.as_view(), name='dashboard'),
    path('inventory/', InventoryPageView.as_view(), name='inventory'),
    path('requests/', RequestsPageView.as_view(), name='requests'),
    path('reports/', ReportPageView.as_view(), name='reports'),
    path('settings/', SettingsPageView.as_view(), name='settings'),
]