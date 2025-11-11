# Quick Commands for Django Shell Testing
# Run: py manage.py shell

from datetime import date, timedelta
from app.models import BorrowRequestBatch, BorrowRequestItem

# Find an active borrow request
active_batch = BorrowRequestBatch.objects.filter(status='active').first()

if active_batch:
    print(f"Found Batch #{active_batch.id}")
    
    # Update its items to have past return dates
    for item in active_batch.items.all():
        item.return_date = date.today() - timedelta(days=1)  # Yesterday
        item.save()
        print(f"  Updated item: {item.property.property_name} - Return date: {item.return_date}")
    
    print("\nNow refresh the borrow requests page to trigger overdue check!")
else:
    print("No active batches found")

# To manually trigger the overdue check:
BorrowRequestBatch.check_overdue_batches()
print("\nOverdue check completed!")

# Check overdue batches
overdue = BorrowRequestBatch.objects.filter(status='overdue')
print(f"\nOverdue batches: {overdue.count()}")
for batch in overdue:
    print(f"  Batch #{batch.id}: {batch.purpose[:50]}")
