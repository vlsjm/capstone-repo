"""
Test to show the exact error message that should appear
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
    
    print("=" * 70)
    print("CURRENT STOCK STATUS")
    print("=" * 70)
    print(f"\nSupply: {supply.supply_name}")
    print(f"Current Quantity: {qty_info.current_quantity}")
    print(f"Reserved Quantity: {qty_info.reserved_quantity}")
    print(f"Available Quantity: {qty_info.available_quantity}")
    
    print("\n" + "=" * 70)
    print("WHAT HAPPENS WHEN YOU TRY TO APPROVE")
    print("=" * 70)
    
    # Simulate trying to approve 10 when only 10 available
    requested = 10
    available = qty_info.available_quantity
    
    print(f"\nYou're trying to approve: {requested} units")
    print(f"Available quantity: {available} units")
    
    if requested > available:
        print("\n❌ APPROVAL BLOCKED!")
        print("\n🔴 ERROR MESSAGE THAT SHOULD APPEAR:")
        print("-" * 70)
        print(f"Cannot approve {requested} units of {supply.supply_name}.")
        print(f"Only {available} units available")
        print(f"(Current: {qty_info.current_quantity}, Reserved: {qty_info.reserved_quantity}).")
        print("-" * 70)
        
        print("\n📋 WHAT THIS MEANS:")
        print(f"  • Total stock on hand: {qty_info.current_quantity}")
        print(f"  • Already reserved for other requests: {qty_info.reserved_quantity}")
        print(f"  • Available for new approvals: {available}")
        print(f"  • You're trying to approve: {requested}")
        print(f"  • Shortage: {requested - available} units")
    else:
        print("\n✅ APPROVAL WOULD SUCCEED")
        print(f"Enough stock available: {available} >= {requested}")
    
    print("\n" + "=" * 70)
    print("SOLUTION")
    print("=" * 70)
    print("\nIf the error message is NOT appearing in your browser:")
    print("  1. Check the browser console for JavaScript errors")
    print("  2. Look for Django messages at the top of the page")
    print("  3. The page should redirect back to the request detail page")
    print("  4. A red error banner should appear with the message above")
    
    print("\n💡 TIP: Try refreshing the page to see if messages appear")
    
else:
    print("❌ Test supply not found")
