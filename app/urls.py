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
    add_property,
    add_supply,
    edit_property, delete_property, LandingPageView, AdminLoginView,
    UserListView,

)

from django.contrib.auth.views import LoginView, LogoutView

urlpatterns = [
    path('manage-users/', UserListView.as_view(), name='user_list'),  # Fixed
    path('', LandingPageView.as_view(), name='landing'),
    path('login/admin/', AdminLoginView.as_view(), name='login_admin'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('dashboard/', DashboardPageView.as_view(), name='dashboard'),
    path('requests/', RequestsListView.as_view(), name='requests'),
    path('reports/', ReportPageView.as_view(), name='reports'),
    path('activity/', ActivityPageView.as_view(), name='activity'),
    path('supplies/', SupplyListView.as_view(), name='supply_list'),
    path('add-supply/', add_supply, name='add_supply'),  
    path('property/', PropertyListView.as_view(), name='property_list'),
    path('add-property/', add_property, name='add_property'),  
    path('check-out/', CheckOutPageView.as_view(), name='checkout'),
    path('edit-property/<int:id>/', edit_property, name='edit_property'),
    path('delete-property/<int:id>/', delete_property, name='delete_property'),
]
