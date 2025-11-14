"""
Management command to test the automatic scheduler by creating test data
that will trigger near-overdue emails and overdue SMS alerts.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date, timedelta
from app.models import BorrowRequestBatch, BorrowRequestItem, Property, UserProfile
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Create test borrow requests with dates configured to trigger notifications'

    def add_arguments(self, parser):
        parser.add_argument(
            '--overdue',
            action='store_true',
            help='Create an overdue item (return_date is yesterday)',
        )
        parser.add_argument(
            '--near-overdue',
            action='store_true',
            help='Create a near-overdue item (return_date matches trigger date)',
        )
        parser.add_argument(
            '--both',
            action='store_true',
            help='Create both overdue and near-overdue test items',
        )
        parser.add_argument(
            '--user',
            type=int,
            help='User ID to create test request for (default: first USER role user)',
        )

    def handle(self, *args, **options):
        overdue = options.get('overdue')
        near_overdue = options.get('near_overdue')
        both = options.get('both')
        user_id = options.get('user')

        # Default to both if nothing specified
        if not (overdue or near_overdue or both):
            both = True

        self.stdout.write(self.style.WARNING('='*70))
        self.stdout.write(self.style.WARNING('TEST SCHEDULER - Creating test borrow requests'))
        self.stdout.write(self.style.WARNING('='*70))

        # Get or create test user
        if user_id:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'User with ID {user_id} not found'))
                return
        else:
            # Get first user with USER role
            user = User.objects.filter(userprofile__role='USER').first()
            if not user:
                self.stdout.write(self.style.ERROR('No user with USER role found. Create a user first.'))
                return

        # Ensure user has phone number for SMS testing
        try:
            profile = user.userprofile
            if not profile.phone:
                profile.phone = '+1234567890'  # Test phone
                profile.save()
                self.stdout.write(self.style.SUCCESS(f'✓ Added test phone to {user.username}'))
        except UserProfile.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User {user.username} has no profile'))
            return

        # Get a property
        property_item = Property.objects.filter(quantity__gt=0).first()
        if not property_item:
            self.stdout.write(self.style.ERROR('No property found with available quantity'))
            return

        # Test 1: OVERDUE ITEM
        if overdue or both:
            self.stdout.write(self.style.WARNING('\n--- TEST 1: OVERDUE ITEM ---'))
            self._create_overdue_test(user, property_item)

        # Test 2: NEAR-OVERDUE ITEM
        if near_overdue or both:
            self.stdout.write(self.style.WARNING('\n--- TEST 2: NEAR-OVERDUE ITEM ---'))
            self._create_near_overdue_test(user, property_item)

        self.stdout.write(self.style.WARNING('\n' + '='*70))
        self.stdout.write(self.style.SUCCESS('✓ Test data created successfully!'))
        self.stdout.write(self.style.WARNING('='*70))
        self.stdout.write(self.style.WARNING('\nNow run the scheduler tasks to see them trigger:'))
        self.stdout.write(self.style.WARNING('  python manage.py shell'))
        self.stdout.write(self.style.WARNING('  >>> from app.scheduler import check_and_notify_overdue_items, send_near_overdue_reminders'))
        self.stdout.write(self.style.WARNING('  >>> check_and_notify_overdue_items()  # Test overdue SMS'))
        self.stdout.write(self.style.WARNING('  >>> send_near_overdue_reminders()      # Test near-overdue email'))

    def _create_overdue_test(self, user, property_item):
        """Create an overdue borrow request that will trigger SMS immediately."""
        from app.utils import send_sms_alert

        # Create batch with request_date in the past
        request_date = timezone.now() - timedelta(days=10)
        return_date = date.today() - timedelta(days=1)  # Yesterday (overdue!)

        batch = BorrowRequestBatch.objects.create(
            user=user,
            purpose='TEST: Overdue item - scheduler should send SMS',
            status='active',
            request_date=request_date,
        )

        item = BorrowRequestItem.objects.create(
            batch_request=batch,
            property=property_item,
            quantity=1,
            approved_quantity=1,
            return_date=return_date,
            status='overdue',  # Already marked as overdue
            claimed_date=timezone.now() - timedelta(days=9),
            overdue_notified=False,  # NOT notified yet - so SMS will send
        )

        self.stdout.write(f'✓ Created overdue test item:')
        self.stdout.write(f'  Batch ID: {batch.id}')
        self.stdout.write(f'  Item ID: {item.id}')
        self.stdout.write(f'  Property: {property_item.property_name}')
        self.stdout.write(f'  Return Date: {return_date} (OVERDUE by 1 day)')
        self.stdout.write(f'  User: {user.username} ({user.email})')
        self.stdout.write(f'  Phone: {user.userprofile.phone}')
        self.stdout.write(self.style.SUCCESS(f'\n✓ When scheduler runs, it will send SMS to {user.userprofile.phone}'))

    def _create_near_overdue_test(self, user, property_item):
        """Create a near-overdue borrow request that will trigger email immediately."""
        from app.utils import calculate_reminder_trigger_date

        # Create a 10-day borrow with request date 8 days ago
        # This means: 10 days total, 2 days borrowed already = 8 days remaining = 80% remaining
        # With 20% reminder, it should trigger at 20% of 10 = 2 days before return
        # So if return is in 2 days, it should trigger NOW
        request_date = timezone.now() - timedelta(days=8)
        return_date = date.today() + timedelta(days=2)  # In 2 days (should trigger now!)

        batch = BorrowRequestBatch.objects.create(
            user=user,
            purpose='TEST: Near-overdue item - scheduler should send email',
            status='active',
            request_date=request_date,
        )

        item = BorrowRequestItem.objects.create(
            batch_request=batch,
            property=property_item,
            quantity=2,
            approved_quantity=2,
            return_date=return_date,
            status='active',  # Active (not returned yet)
            claimed_date=timezone.now() - timedelta(days=7),
            near_overdue_notified=False,  # NOT notified yet - so email will send
        )

        # Calculate trigger datetime to verify (now returns datetime, not date)
        trigger_datetime = calculate_reminder_trigger_date(
            batch.request_date.date(),
            return_date
        )

        self.stdout.write(f'✓ Created near-overdue test item:')
        self.stdout.write(f'  Batch ID: {batch.id}')
        self.stdout.write(f'  Item ID: {item.id}')
        self.stdout.write(f'  Property: {property_item.property_name}')
        self.stdout.write(f'  Request Date: {batch.request_date.date()}')
        self.stdout.write(f'  Return Date: {return_date} (in 2 days)')
        self.stdout.write(f'  Trigger DateTime: {trigger_datetime} (should trigger based on current time!)')
        self.stdout.write(f'  User: {user.username} ({user.email})')
        self.stdout.write(self.style.SUCCESS(f'\n✓ When scheduler runs, it will send email to {user.email}'))
