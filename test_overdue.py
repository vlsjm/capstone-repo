"""
Test script to create overdue borrow requests for testing
Run this with: py test_overdue.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ResourceHive.settings')
django.setup()

from datetime import date, timedelta
from app.models import BorrowRequestBatch, BorrowRequestItem, Property, User
from django.utils import timezone

def create_test_overdue_requests():
    """Create test borrow requests with past return dates"""
    
    # Get or create a test user
    test_user = User.objects.filter(username='DCS').first()
    if not test_user:
        print("No test user found. Please specify a valid username.")
        return
    
    # Get available properties
    properties = Property.objects.filter(availability='available')[:3]
    
    if not properties:
        print("No available properties found.")
        return
    
    print(f"Creating test overdue borrow requests for user: {test_user.username}")
    print("=" * 60)
    
    # Create test scenarios
    test_scenarios = [
        {
            'days_overdue': 1,
            'description': 'Overdue by 1 day (yesterday)'
        },
        {
            'days_overdue': 3,
            'description': 'Overdue by 3 days'
        },
        {
            'days_overdue': 7,
            'description': 'Overdue by 1 week'
        }
    ]
    
    for i, scenario in enumerate(test_scenarios, 1):
        if i > len(properties):
            break
            
        property_obj = properties[i-1]
        days_overdue = scenario['days_overdue']
        return_date = date.today() - timedelta(days=days_overdue)
        
        # Create batch request
        batch = BorrowRequestBatch.objects.create(
            user=test_user,
            purpose=f"TEST: {scenario['description']}",
            status='active',  # Start as active
        )
        
        # Create batch item with past return date
        item = BorrowRequestItem.objects.create(
            batch_request=batch,
            property=property_obj,
            quantity=1,
            approved_quantity=1,
            status='active',
            approved=True,
            return_date=return_date,
        )
        
        # Set claimed date to a few days before return date
        batch.claimed_date = timezone.now() - timedelta(days=days_overdue + 2)
        batch.save()
        
        print(f"\n✅ Created Test Batch #{batch.id}:")
        print(f"   Property: {property_obj.property_name}")
        print(f"   Return Date: {return_date} ({days_overdue} days ago)")
        print(f"   Status: {batch.status}")
        print(f"   {scenario['description']}")
    
    print("\n" + "=" * 60)
    print("\n📋 Next Steps:")
    print("1. Go to the Borrow Requests page")
    print("2. Refresh the page (this will trigger check_overdue_batches())")
    print("3. Check the 'Overdue' tab - you should see the test requests there")
    print("\n💡 To clean up test data later, note the batch IDs above")

if __name__ == '__main__':
    create_test_overdue_requests()
