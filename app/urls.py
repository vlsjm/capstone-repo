from django.urls import path
from django.contrib.auth.views import LogoutView
from .views import (
    LandingPageView,
    # AdminLoginView,
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
    create_user,
    request_detail,
    borrow_request_details,
    damage_report_detail,
    reservation_detail,
    mark_notification_as_read_ajax,
    mark_all_notifications_as_read,
    clear_all_notifications,
    logout_view,
    create_supply_request,
    create_borrow_request,
    approve_supply_request,
    approve_borrow_request,
    reject_supply_request,
    reject_borrow_request,
    get_supply_history,
    get_property_history,
    CustomLoginView
)

urlpatterns = [
    path('', LandingPageView.as_view(), name='landing'),
    # path('login/admin/', AdminLoginView.as_view(), name='login_admin'),
    path('accounts/login/', CustomLoginView.as_view(), name='login'),
    path('logout/', logout_view, name='logout'),

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

    path('create-supply-request/', create_supply_request, name='create_supply_request'),
    path('create-borrow-request/', create_borrow_request, name='create_borrow_request'),
    path('approve-supply-request/<int:request_id>/', approve_supply_request, name='approve_supply_request'),
    path('approve-borrow-request/<int:request_id>/', approve_borrow_request, name='approve_borrow_request'),
    path('reject-supply-request/<int:request_id>/', reject_supply_request, name='reject_supply_request'),
    path('reject-borrow-request/<int:request_id>/', reject_borrow_request, name='reject_borrow_request'),

    path('request/<int:pk>/', request_detail, name='request_detail'),
    path('borrow-request/<int:pk>/', borrow_request_details, name='borrow_request_details'),
    path('damage-report/<int:pk>/', damage_report_detail, name='damage_report_detail'),
    path('reservation/<int:pk>/', reservation_detail, name='reservation_detail'),

    path('mark-notification-read/', mark_notification_as_read_ajax, name='mark_notification_read'),
    path('mark-all-notifications-read/', mark_all_notifications_as_read, name='mark_all_notifications_read'),
    path('clear-all-notifications/', clear_all_notifications, name='clear_all_notifications'),

    path('api/supply/<int:supply_id>/history/', get_supply_history, name='supply_history'),
    path('api/property/<int:property_id>/history/', get_property_history, name='property_history'),

    path('get_supply_history/<int:supply_id>/', get_supply_history, name='get_supply_history'),
    path('get_property_history/<int:property_id>/', get_property_history, name='get_property_history'),
]
