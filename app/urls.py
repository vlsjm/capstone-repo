from django.urls import path
from . import views
from .views import (
    DashboardPageView,
    RequestsListView,
    ReportPageView,
    ActivityPageView,
    SupplyListView,
    PropertyListView,
    CheckOutPageView,
    ManageUsersPageView,
    add_property,
    add_supply,
    edit_property, delete_property
)

urlpatterns = [
    path('', DashboardPageView.as_view(), name='dashboard'),
    path('requests/', RequestsListView.as_view(), name='requests'),
    path('reports/', ReportPageView.as_view(), name='reports'),
    path('activity/', ActivityPageView.as_view(), name='activity'),
    path('supplies/', SupplyListView.as_view(), name='supply_list'),
    path('add-supply/', add_supply, name='add_supply'),  # URL to add supply
    path('property/', PropertyListView.as_view(), name='property_list'),
    path('add-property/', add_property, name='add_property'),  # URL to add property
    path('check-out/', CheckOutPageView.as_view(), name='checkout'),
    path('manage-users/', ManageUsersPageView.as_view(), name='manage_users'),
    path('edit-property/<int:id>/', edit_property, name='edit_property'),
    path('delete-property/<int:id>/', delete_property, name='delete_property'),

]