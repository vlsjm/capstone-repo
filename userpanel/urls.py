from django.urls import path
from django.contrib.auth.views import PasswordChangeView, PasswordChangeDoneView
from django.contrib.auth.decorators import login_required
from .views import (
    UserDashboardView,
    UserRequestView,
    UserReserveView,
    UserReportView,
    UserLoginView,
    UserBorrowView,
    UserPasswordChangeView,
    UserPasswordChangeDoneView,
)
from . import views

urlpatterns = [
    path('user_dashboard/', UserDashboardView.as_view(), name='user_dashboard'),
    path('user_request/', UserRequestView.as_view(), name='user_request'),
    path('user_reserve/', UserReserveView.as_view(), name='user_reserve'),
    path('user_report/', UserReportView.as_view(), name='user_report'),
    path('login/user/', UserLoginView.as_view(), name='login_user'),  
    path('user_borrow/', UserBorrowView.as_view(), name='user_borrow'),
    path('get-item-availability/', views.get_item_availability, name='get_item_availability'),
    
    # Password change URLs with custom views
    path('password/change/', 
         UserPasswordChangeView.as_view(), 
         name='user_password_change'),
    path('password/change/done/', 
         UserPasswordChangeDoneView.as_view(), 
         name='user_password_change_done'),
    path('cancel-supply-request/<int:request_id>/', views.cancel_supply_request, name='cancel_supply_request'),
    path('cancel-borrow-request/<int:request_id>/', views.cancel_borrow_request, name='cancel_borrow_request'),
    path('cancel-reservation/<int:request_id>/', views.cancel_reservation, name='cancel_reservation'),
    path('cancel-damage-report/<int:request_id>/', views.cancel_damage_report, name='cancel_damage_report'),
]