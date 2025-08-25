#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ResourceHive.settings')
django.setup()

# Now we can import Django models
from app.models import SupplyRequestBatch, SupplyRequestItem, Supply
from django.contrib.auth.models import User

def test_cart_functionality():
    print("=== Testing Cart Functionality ===\n")
    
    # Check if new models exist
    batch_count = SupplyRequestBatch.objects.count()
    item_count = SupplyRequestItem.objects.count()
    
    print(f"SupplyRequestBatch records: {batch_count}")
    print(f"SupplyRequestItem records: {item_count}")
    print()
    
    # Check available supplies for cart
    available_supplies = Supply.objects.filter(
        available_for_request=True,
        quantity_info__current_quantity__gt=0
    )
    
    print(f"Available supplies for cart: {available_supplies.count()}")
    for supply in available_supplies[:5]:  # Show first 5
        print(f"- {supply.supply_name} ({supply.quantity_info.current_quantity} available)")
    print()
    
    # Show recent batch requests if any
    recent_batches = SupplyRequestBatch.objects.order_by('-request_date')[:3]
    if recent_batches:
        print("Recent batch requests:")
        for batch in recent_batches:
            print(f"- Batch #{batch.id} by {batch.user.username}")
            print(f"  Status: {batch.status}")
            print(f"  Items: {batch.total_items}")
            print(f"  Total Quantity: {batch.total_quantity}")
            print(f"  Purpose: {batch.purpose[:50]}...")
            for item in batch.items.all():
                print(f"    - {item.supply.supply_name} x{item.quantity}")
            print()
    else:
        print("No batch requests found yet.")
        print("Visit http://127.0.0.1:8000/create-supply-request/ to test the cart!")
    
    print("\n=== Cart URLs Available ===")
    print("Main cart page: http://127.0.0.1:8000/create-supply-request/")
    print("Add to cart: POST to /add-to-cart/")
    print("Remove from cart: POST to /remove-from-cart/")
    print("Update cart: POST to /update-cart-item/")
    print("Submit request: POST to /submit-cart-request/")

if __name__ == "__main__":
    test_cart_functionality()
