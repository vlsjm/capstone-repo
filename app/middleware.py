from django.utils.deprecation import MiddlewareMixin
from django.utils.cache import add_never_cache_headers
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import reverse
from django.http import HttpResponseRedirect
from .models import UserSession

class DisableClientSideCachingMiddleware(MiddlewareMixin):
    """
    Prevent caching of authenticated pages to ensure back button doesn't work
    """
    def process_response(self, request, response):
        # Add no-cache headers for all responses
        add_never_cache_headers(response)
        
        # For authenticated users, add additional headers to prevent back button from working
        if request.user.is_authenticated:
            response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0, private'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        
        return response


class PreventBackToLoginMiddleware(MiddlewareMixin):
    """
    Redirect authenticated users away from login page if they try to access it via back button
    """
    def process_request(self, request):
        # Check if user is authenticated and trying to access login page
        if request.user.is_authenticated:
            # List of login-related URLs to protect
            protected_paths = ['/accounts/login/', '/login/', '/auth/login/']
            current_path = request.path.lower()
            
            if any(path in current_path for path in protected_paths):
                # Redirect authenticated users away from login
                if request.user.groups.filter(name='ADMIN').exists():
                    return HttpResponseRedirect(reverse('dashboard'))
                elif request.user.groups.filter(name='USER').exists():
                    return HttpResponseRedirect(reverse('user_dashboard'))
                else:
                    return HttpResponseRedirect(reverse('dashboard'))
        
        return None


class SingleSessionPerUserMiddleware(MiddlewareMixin):
    """
    Middleware to enforce 1 active session per user.
    If a user logs in from a different device/browser, the previous session will be invalidated.
    """
    
    def process_request(self, request):
        """Check if the current session is still valid for this user"""
        if not isinstance(request.user, AnonymousUser) and request.user.is_authenticated:
            try:
                # Only validate if we have a session key
                if not request.session.session_key:
                    return None
                    
                user_session = UserSession.objects.get(user=request.user)
                
                # Check if the current session key matches the stored session key
                if request.session.session_key != user_session.session_key:
                    # Session key mismatch - invalidate current session
                    logout(request)
                    return redirect(reverse('login'))
                    
            except UserSession.DoesNotExist:
                # No active session record - create one if we have a session key
                if request.session.session_key:
                    try:
                        UserSession.objects.update_or_create(
                            user=request.user,
                            defaults={
                                'session_key': request.session.session_key,
                                'ip_address': self.get_client_ip(request),
                                'user_agent': request.META.get('HTTP_USER_AGENT', '')[:500]
                            }
                        )
                    except Exception:
                        # Silently fail if we can't create session record
                        pass
            except Exception:
                # Silently fail for any other exception
                pass
        
        return None
    
    @staticmethod
    def get_client_ip(request):
        """Get the client's IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
