from django.urls import path
from django.contrib.auth.views import LogoutView
from .views import (
    LandingPageView,
    AdminLoginView,
    DashboardPageView,
    UserBorrowRequestListView,
    UserSupplyRequestListView,
    UserDamageReportListView,
    UserReservationListView,
    ActivityPageView,
    SupplyListView,
    PropertyListView,
    CheckOutPageView,
    UserProfileListView,
    add_property,
    add_supply,
    edit_property,
    delete_property,
    edit_supply,
    delete_supply,
    create_user
)

urlpatterns = [
    path('', LandingPageView.as_view(), name='landing'),
    path('login/admin/', AdminLoginView.as_view(), name='login_admin'),
    path('logout/', LogoutView.as_view(), name='logout'),

    path('dashboard/', DashboardPageView.as_view(), name='dashboard'),
    path('activity/', ActivityPageView.as_view(), name='activity'),

    path('supplies/', SupplyListView.as_view(), name='supply_list'),
    path('add-supply/', add_supply, name='add_supply'),
    path('edit-supply/', edit_supply, name='edit_supply'),
    path('delete-supply/<int:pk>/', delete_supply, name='delete_supply'),

    path('property/', PropertyListView.as_view(), name='property_list'),
    path('add-property/', add_property, name='add_property'),
    path('edit-property/', edit_property, name='edit_property'),
    path('delete-property/<int:pk>/', delete_property, name='delete_property'),

    path('check-out/', CheckOutPageView.as_view(), name='checkout'),

    path('manage-users/', UserProfileListView.as_view(), name='manage_users'),
    path('create-user/', create_user, name='create_user'),

    path('my-borrow-requests/', UserBorrowRequestListView.as_view(), name='user_borrow_requests'),
    path('my-supply-requests/', UserSupplyRequestListView.as_view(), name='user_supply_requests'),
    path('my-damage-reports/', UserDamageReportListView.as_view(), name='user_damage_reports'),
    path('my-reservations/', UserReservationListView.as_view(), name='user_reservations'),
]