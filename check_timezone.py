#!/usr/bin/env python
import os
import django
import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ResourceHive.settings')
django.setup()

from django.utils import timezone

now_django = timezone.now()
print(f"Django timezone.now(): {now_django}")
print(f"Django timezone.now().date(): {now_django.date()}")
print(f"Python datetime.now(): {datetime.datetime.now()}")
print(f"Current timezone: {timezone.get_current_timezone()}")

# Check what the system is configured as
import time
print(f"\nSystem timezone: {time.tzname}")
print(f"System localtime: {datetime.datetime.fromtimestamp(time.time())}")
