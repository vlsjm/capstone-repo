from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.views import LoginView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login_user/', LoginView.as_view(template_name='registration/login.html'), name='login_user'),
    path('', include('app.urls')),
    path('accounts/', include('accounts.urls')),
    path('userpanel/', include('userpanel.urls')),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

