from django import template

register = template.Library()

@register.filter
def get_department(user):
    """
    Safely get user's department, handling missing UserProfile.
    Usage: {{ user|get_department }}
    """
    try:
        if hasattr(user, 'userprofile') and user.userprofile:
            return user.userprofile.department if user.userprofile.department else 'No Department'
        return 'No Department'
    except:
        return 'No Department'

@register.filter
def get_role(user):
    """
    Safely get user's role, handling missing UserProfile.
    Usage: {{ user|get_role }}
    """
    try:
        if hasattr(user, 'userprofile') and user.userprofile:
            return user.userprofile.role
        return 'USER'
    except:
        return 'USER'
