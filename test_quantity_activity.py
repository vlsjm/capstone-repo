#!/usr/bin/env python
"""
Test script for quantity activity endpoints
"""
import os
import sys
import django
from datetime import datetime

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ResourceHive.settings')
django.setup()

from app.models import Supply, SupplyHistory, SupplyCategory, SupplyQuantity
from django.contrib.auth.models import User

def test_quantity_activity():
    """Test the quantity activity functionality"""
    print("Testing Quantity Activity Feature")
    print("=" * 50)
    
    # Check if we have any supplies
    supply_count = Supply.objects.count()
    print(f"Total supplies in database: {supply_count}")
    
    if supply_count == 0:
        print("No supplies found. Creating test supply...")
        
        # Create a test category if it doesn't exist
        category, created = SupplyCategory.objects.get_or_create(name="Test Category")
        
        # Create a test supply
        supply = Supply.objects.create(
            supply_name="Test Supply for Quantity Activity",
            category=category,
            description="Test supply for testing quantity activity feature"
        )
        
        # Create quantity info
        quantity_info = SupplyQuantity.objects.create(
            supply=supply,
            current_quantity=50,
            minimum_threshold=10
        )
        
        print(f"Created test supply: {supply.supply_name} (ID: {supply.id})")
    else:
        # Use the first supply
        supply = Supply.objects.first()
        print(f"Using existing supply: {supply.supply_name} (ID: {supply.id})")
    
    # Check quantity history
    history_count = SupplyHistory.objects.filter(
        supply=supply,
        field_name__in=['quantity', 'current_quantity', 'initial_quantity']
    ).count()
    print(f"Quantity history entries for {supply.supply_name}: {history_count}")
    
    # Create some test history if none exists
    if history_count == 0:
        print("Creating test quantity history...")
        
        # Create test user if needed
        user, created = User.objects.get_or_create(
            username='testuser',
            defaults={'first_name': 'Test', 'last_name': 'User'}
        )
        
        # Create some history entries
        SupplyHistory.objects.create(
            supply=supply,
            user=user,
            action='create',
            field_name='initial_quantity',
            old_value=None,
            new_value='50',
            remarks='Initial quantity set'
        )
        
        SupplyHistory.objects.create(
            supply=supply,
            user=user,
            action='update',
            field_name='current_quantity',
            old_value='50',
            new_value='75',
            remarks='Added 25 units'
        )
        
        SupplyHistory.objects.create(
            supply=supply,
            user=user,
            action='update',
            field_name='current_quantity',
            old_value='75',
            new_value='65',
            remarks='Used 10 units'
        )
        
        print("Created test quantity history entries")
    
    # Now test our endpoint logic
    print("\nTesting endpoint logic:")
    
    quantity_history = supply.history.filter(
        field_name__in=['quantity', 'current_quantity', 'initial_quantity']
    ).order_by('-timestamp')
    
    print(f"Found {quantity_history.count()} quantity history entries")
    
    activity_data = []
    total_additions = 0
    total_deductions = 0
    
    for entry in quantity_history:
        try:
            old_qty = int(entry.old_value) if entry.old_value and entry.old_value.isdigit() else 0
            new_qty = int(entry.new_value) if entry.new_value and entry.new_value.isdigit() else 0
            quantity_change = new_qty - old_qty
            
            if entry.action == 'create':
                action_type = 'Initial Creation'
                quantity_change = new_qty
            elif quantity_change > 0:
                action_type = 'Addition'
                total_additions += quantity_change
            elif quantity_change < 0:
                action_type = 'Deduction'
                total_deductions += abs(quantity_change)
            else:
                action_type = 'Adjustment'
            
            activity_data.append({
                'date': entry.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'action': action_type,
                'quantity_change': quantity_change,
                'previous_quantity': old_qty,
                'new_quantity': new_qty,
                'user': entry.user.username if entry.user else 'System',
                'remarks': entry.remarks if entry.remarks else 'N/A'
            })
            
            print(f"  - {entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}: {action_type} ({quantity_change:+d}) - {old_qty} → {new_qty}")
            
        except Exception as e:
            print(f"  Error processing entry {entry.id}: {str(e)}")
    
    net_change = total_additions - total_deductions
    
    print(f"\nSummary:")
    print(f"  Total Additions: {total_additions}")
    print(f"  Total Deductions: {total_deductions}")
    print(f"  Net Change: {net_change}")
    print(f"  Total Transactions: {len(activity_data)}")
    
    print(f"\nTest Supply ID for frontend testing: {supply.id}")
    print(f"URL to test: http://127.0.0.1:8000/get_supply_quantity_activity/{supply.id}/")
    
    return supply.id

if __name__ == "__main__":
    test_quantity_activity()