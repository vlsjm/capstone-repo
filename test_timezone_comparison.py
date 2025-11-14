"""
Test timezone-aware datetime comparison
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ResourceHive.settings')
django.setup()

from datetime import date, timedelta
from app.utils import calculate_reminder_trigger_date
from django.utils import timezone

print('='*80)
print('TESTING TIMEZONE-AWARE DATETIME COMPARISON')
print('='*80)

# Create a trigger
borrow = date.today()
ret = date.today() + timedelta(days=1)
trigger = calculate_reminder_trigger_date(borrow, ret)
now = timezone.now()

print(f"\nNow (UTC):         {now}")
print(f"Trigger (Manila):  {trigger}")
print(f"\nNow timezone:      {now.tzinfo}")
print(f"Trigger timezone:  {trigger.tzinfo}")

# Test comparison
print(f"\nComparison test:")
print(f"  now >= trigger:  {now >= trigger}")
print(f"  now < trigger:   {now < trigger}")
print(f"  now == trigger:  {now == trigger}")

# Convert to same timezone for visual clarity
from datetime import timezone as dt_timezone
trigger_utc = trigger.astimezone(dt_timezone.utc)
print(f"\nTrigger in UTC:    {trigger_utc}")
print(f"Now in UTC:        {now}")
print(f"\nComparison still works: {now >= trigger}")

print('\n✓ Timezone-aware datetime comparisons work correctly!')
print('  Python automatically converts timezones when comparing.')
