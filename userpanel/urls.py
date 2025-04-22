from django.urls import path
from .views import UserDashboardView, UserRequestView, UserReserveView, UserReportView

urlpatterns = [
    path('user_dashboard/', UserDashboardView.as_view(), name='user_dashboard'),
    path('user_request/', UserRequestView.as_view(), name='user_request'),
    path('user_reserve/', UserReserveView.as_view(), name='user_reserve'),
    path('user_report/', UserReportView.as_view(), name='user_report'),
]
