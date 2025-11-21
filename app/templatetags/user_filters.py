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

@register.filter
def get(dictionary, key):
    """
    Get a value from a dictionary using a key.
    Usage: {{ dictionary|get:key }}
    """
    try:
        if isinstance(dictionary, dict):
            return dictionary.get(str(key), '')
        return ''
    except:
        return ''

@register.filter
def multiply(value, arg):
    """
    Multiply a value by an argument.
    Usage: {{ value|multiply:100 }}
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def divide(value, arg):
    """
    Divide a value by an argument.
    Usage: {{ value|divide:item_data.requested }}
    """
    try:
        if float(arg) == 0:
            return 0
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

