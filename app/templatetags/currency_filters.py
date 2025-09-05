from django import template
from decimal import Decimal, InvalidOperation

register = template.Library()

@register.filter
def peso(value):
    """
    Format a number as Philippine peso currency.
    Usage: {{ value|peso }}
    """
    if value is None or value == '':
        return "₱0.00"
    
    try:
        # Convert to Decimal for precise formatting
        if isinstance(value, str):
            # Remove any existing currency symbols and commas
            clean_value = value.replace('₱', '').replace(',', '').strip()
            decimal_value = Decimal(clean_value)
        else:
            decimal_value = Decimal(str(value))
        
        # Format with commas and 2 decimal places
        formatted = "{:,.2f}".format(float(decimal_value))
        return f"₱{formatted}"
    
    except (InvalidOperation, ValueError, TypeError):
        return "₱0.00"
