from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from app.models import UserProfile


class ForcePasswordChangeMiddleware:
    """
    Middleware to force users to change their password if must_change_password is True.
    Applies to both USER and ADMIN roles.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Check if user is authenticated
        if request.user.is_authenticated:
            try:
                profile = UserProfile.objects.get(user=request.user)
                
                # Check for both USER and ADMIN roles that need password change
                if (profile.role == 'USER' or profile.role == 'ADMIN') and profile.must_change_password:
                    current_path = request.path
                    
                    # URLs that should be accessible even when password change is required
                    if profile.role == 'USER':
                        allowed_urls = [
                            '/auth/password_change/',
                            '/user/password_change/',
                            '/accounts/password_change/',
                            reverse('user_password_change'),
                            reverse('user_password_change_done'),
                            reverse('logout'),
                            '/static/',
                            '/media/',
                        ]
                        redirect_url = 'user_password_change'
                    else:  # ADMIN
                        allowed_urls = [
                            '/password_change/',
                            '/auth/password_change/',
                            reverse('password_change'),
                            reverse('password_change_done'),
                            reverse('logout'),
                            '/static/',
                            '/media/',
                        ]
                        redirect_url = 'password_change'
                    
                    # Skip check if on allowed URLs
                    is_allowed = any(current_path.startswith(url) for url in allowed_urls)
                    
                    if not is_allowed:
                        messages.warning(request, 'You must change your password before accessing other pages.')
                        return redirect(redirect_url)
                        
            except UserProfile.DoesNotExist:
                pass
        
        response = self.get_response(request)
        return response
