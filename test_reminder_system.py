"""
Test script for the new short-term borrow reminder system
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ResourceHive.settings')
django.setup()

from datetime import date, timedelta
from app.utils import calculate_reminder_trigger_date
from django.utils import timezone

print('='*80)
print('COMPREHENSIVE REMINDER TRIGGER TESTING')
print('='*80)
print()

tests = [
    (0, 'SAME DAY'),
    (1, '1 DAY'),
    (2, '2 DAYS'),
    (3, '3 DAYS'),
    (7, '1 WEEK'),
    (14, '2 WEEKS'),
    (30, '1 MONTH'),
]

now = timezone.now()
print(f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
print()

for days, label in tests:
    borrow = date.today()
    ret = date.today() + timedelta(days=days)
    trigger = calculate_reminder_trigger_date(borrow, ret)
    
    will_trigger = 'YES ✓' if now >= trigger else 'NO ✗'
    hours_until = (trigger - now).total_seconds() / 3600
    
    print(f'{label:12} | Return: {ret} | Trigger: {trigger.strftime("%Y-%m-%d %H:%M")} | Will trigger now: {will_trigger:6} | Hours until: {hours_until:>6.1f}h')

print()
print('='*80)
print('TIMEZONE AWARENESS CHECK')
print('='*80)

test_trigger = calculate_reminder_trigger_date(date.today(), date.today() + timedelta(days=1))
print(f"Trigger datetime: {test_trigger}")
print(f"Is timezone-aware: {test_trigger.tzinfo is not None}")
print(f"Timezone: {test_trigger.tzinfo}")
print(f"Can compare with timezone.now(): {isinstance(test_trigger.tzinfo, type(now.tzinfo))}")

print()
print('='*80)
print('SAME-DAY BORROW EDGE CASE')
print('='*80)

same_day_trigger = calculate_reminder_trigger_date(date.today(), date.today())
print(f"Same-day borrow trigger: {same_day_trigger}")
print(f"Current time: {now}")
print(f"Will trigger immediately: {now >= same_day_trigger}")
print(f"Hours until trigger: {(same_day_trigger - now).total_seconds() / 3600:.1f}h")
