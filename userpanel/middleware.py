from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from app.models import UserProfile


class ForcePasswordChangeMiddleware:
    """
    Middleware to force users to change their password if must_change_password is True.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # URLs that should be accessible even when password change is required
        allowed_urls = [
            reverse('user_password_change'),
            reverse('user_password_change_done'),
            reverse('logout'),
            '/static/',
            '/media/',
        ]
        
        # Check if user is authenticated and not on an allowed URL
        if request.user.is_authenticated:
            current_path = request.path
            
            # Skip check if on allowed URLs
            is_allowed = any(current_path.startswith(url) for url in allowed_urls)
            
            if not is_allowed:
                try:
                    profile = UserProfile.objects.get(user=request.user)
                    
                    # Only check for USER role (not ADMIN)
                    if profile.role == 'USER' and profile.must_change_password:
                        # Redirect to password change page
                        if current_path != reverse('user_password_change'):
                            messages.warning(request, 'You must change your password before accessing other pages.')
                            return redirect('user_password_change')
                            
                except UserProfile.DoesNotExist:
                    pass
        
        response = self.get_response(request)
        return response
