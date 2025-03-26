from django.urls import path
from .views import (
    DashboardPageView,
    RequestsListView,
    ReportPageView,
    ActivityPageView,
    SupplyListView,
    PropertyListView,
    CheckOutPageView,
    ManageUsersPageView,

)

urlpatterns = [
    path('', DashboardPageView.as_view(), name='dashboard'),
    path('requests/', RequestsListView.as_view(), name='requests'),
    path('reports/', ReportPageView.as_view(), name='reports'),
    path('activity/', ActivityPageView.as_view(), name='activity'),
    path('supplies/', SupplyListView.as_view(), name='supply_list'),
    path('property/', PropertyListView.as_view(), name='property_list'),
    path('check-out/', CheckOutPageView.as_view(), name='checkout'),
    path('manage-users/', ManageUsersPageView.as_view(), name='manage_users'),


]