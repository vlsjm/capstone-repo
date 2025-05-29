from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.views import LoginView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login_user/', LoginView.as_view(template_name='registration/login.html'), name='login_user'),
    path('', include('app.urls')),
    path('accounts/', include('accounts.urls')),
    path('accounts/', include('django.contrib.auth.urls')),   
    path('userpanel/', include('userpanel.urls')),
]

