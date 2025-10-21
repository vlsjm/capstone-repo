"""
Reset the test supply to initial state
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ResourceHive.settings')
django.setup()

from app.models import Supply

# Find the test supply
supply = Supply.objects.filter(supply_name__icontains='TEST FOR OVERBOOKING').first()

if supply:
    qty_info = supply.quantity_info
    print(f"Found: {supply.supply_name}")
    print(f"Before: Current={qty_info.current_quantity}, Reserved={qty_info.reserved_quantity}")
    
    # Reset to clean state
    qty_info.current_quantity = 10
    qty_info.reserved_quantity = 0
    qty_info.save()
    
    print(f"After:  Current={qty_info.current_quantity}, Reserved={qty_info.reserved_quantity}")
    print(f"Available: {qty_info.available_quantity}")
    print("\n✅ Reset complete!")
else:
    print("❌ Test supply not found")
