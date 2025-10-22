from django.urls import path
from .views import RegisterCreateView, check_email_availability

urlpatterns = [
    path('register/', RegisterCreateView.as_view(), name='register'),
    path('check-email/', check_email_availability, name='check_email'),
]
