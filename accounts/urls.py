from django.urls import path
from django.contrib.auth.views import LoginView
from .views import RegisterCreateView, check_email_availability

urlpatterns = [
    path('login/', LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('register/', RegisterCreateView.as_view(), name='register'),
    path('check-email/', check_email_availability, name='check_email'),
]
