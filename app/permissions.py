"""
Custom permission utilities for admin access control
"""
from functools import wraps
from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages
from django.http import JsonResponse


def has_admin_permission(user, permission_codename):
    """
    Check if a user has a specific admin permission
    
    Args:
        user: User object
        permission_codename: String codename of the permission (e.g., 'approve_supply_request')
    
    Returns:
        Boolean indicating if user has the permission
    """
    if not user.is_authenticated:
        return False
    
    # Superusers have all permissions
    if user.is_superuser:
        return True
    
    try:
        profile = user.userprofile
    except:
        return False
    
    return profile.has_admin_permission(permission_codename)


def admin_permission_required(permission_codename, redirect_url='/dashboard/', raise_exception=True):
    """
    Decorator for views that checks whether a user has a specific admin permission.
    
    Args:
        permission_codename: The codename of the required permission
        redirect_url: URL to redirect to if permission is denied (default: dashboard)
        raise_exception: If True, raise PermissionDenied to show 403 page (default: True)
    
    Usage:
        @admin_permission_required('approve_supply_request')
        def my_view(request):
            # View code here
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)
                return redirect('login')
            
            if has_admin_permission(request.user, permission_codename):
                return view_func(request, *args, **kwargs)
            
            # For AJAX requests, return JSON error immediately
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False, 
                    'error': "You don't have permission to perform this action."
                }, status=403)
            
            # Raise PermissionDenied to show 403.html page
            if raise_exception:
                raise PermissionDenied("You don't have permission to access this resource.")
            
            # Fallback: redirect with message
            messages.error(request, "You don't have permission to perform this action.")
            referer = request.META.get('HTTP_REFERER')
            if referer:
                return redirect(referer)
            return redirect(redirect_url)
        
        return wrapper
    return decorator


def check_multiple_permissions(user, permission_codenames, require_all=True):
    """
    Check if user has multiple permissions
    
    Args:
        user: User object
        permission_codenames: List of permission codenames
        require_all: If True, user must have ALL permissions. If False, user needs ANY permission.
    
    Returns:
        Boolean
    """
    if not user.is_authenticated:
        return False
    
    if user.is_superuser:
        return True
    
    try:
        profile = user.userprofile
    except:
        return False
    
    if require_all:
        return all(profile.has_admin_permission(perm) for perm in permission_codenames)
    else:
        return any(profile.has_admin_permission(perm) for perm in permission_codenames)


class AdminPermissionMixin:
    """
    Mixin for class-based views that require admin permission
    
    Usage:
        class MyView(AdminPermissionMixin, View):
            required_permission = 'approve_supply_request'
            # or for multiple permissions:
            required_permissions = ['approve_supply_request', 'edit_supply']
            require_all_permissions = True  # default True
    """
    required_permission = None
    required_permissions = None
    require_all_permissions = True
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        # Check single permission
        if self.required_permission:
            if not has_admin_permission(request.user, self.required_permission):
                raise PermissionDenied("You don't have permission to access this page.")
        
        # Check multiple permissions
        elif self.required_permissions:
            if not check_multiple_permissions(
                request.user, 
                self.required_permissions, 
                self.require_all_permissions
            ):
                raise PermissionDenied("You don't have permission to access this page.")
        
        return super().dispatch(request, *args, **kwargs)


def get_user_admin_permissions(user):
    """
    Get a dictionary of all admin permissions for a user
    Returns dict with permission codenames as keys and boolean values
    """
    from app.models import AdminPermission
    
    if not user.is_authenticated:
        return {}
    
    try:
        profile = user.userprofile
    except:
        return {}
    
    permissions = {}
    for perm in AdminPermission.objects.all():
        permissions[perm.codename] = profile.has_admin_permission(perm.codename)
    
    return permissions


def filter_admin_queryset_by_permission(user, queryset, permission_codename):
    """
    Helper to filter querysets based on permissions
    Returns queryset or empty queryset based on permission
    """
    if has_admin_permission(user, permission_codename):
        return queryset
    return queryset.none()
