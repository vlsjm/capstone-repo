from django.core.management.base import BaseCommand
from app.models import BorrowRequestBatch, BorrowRequestItem, Property, User
from app.utils import send_near_overdue_borrow_email, calculate_reminder_trigger_date
from datetime import date, timedelta
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Test near-overdue email notification by creating test data and sending email'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            help='User ID to send test email to (if not provided, uses first user)'
        )
        parser.add_argument(
            '--property-id',
            type=int,
            help='Property ID to use for test item (if not provided, uses first property)'
        )
        parser.add_argument(
            '--days-until-return',
            type=int,
            default=2,
            help='How many days until return date (default: 2)'
        )

    def handle(self, *args, **options):
        user_id = options.get('user_id')
        property_id = options.get('property_id')
        days_until_return = options['days_until_return']

        # Get user
        if user_id:
            user = User.objects.get(id=user_id)
        else:
            user = User.objects.filter(userprofile__role='USER').first()

        if not user:
            self.stdout.write(self.style.ERROR('No user found. Create a user first.'))
            return

        # Get property
        if property_id:
            property_item = Property.objects.get(id=property_id)
        else:
            property_item = Property.objects.first()

        if not property_item:
            self.stdout.write(self.style.ERROR('No property found. Create a property first.'))
            return

        self.stdout.write(self.style.WARNING('Creating test data...'))

        # Create a test batch
        batch = BorrowRequestBatch.objects.create(
            user=user,
            purpose="Test near-overdue reminder email",
            status='active',
            request_date=timezone.now() - timedelta(days=5),
            approved_date=timezone.now() - timedelta(days=4)
        )

        # Create item with return date that should trigger reminder
        return_date = date.today() + timedelta(days=days_until_return)

        item = BorrowRequestItem.objects.create(
            batch_request=batch,
            property=property_item,
            quantity=2,
            approved_quantity=2,
            return_date=return_date,
            status='active'
        )

        self.stdout.write(
            self.style.SUCCESS(f'✓ Created test batch #{batch.id}')
        )
        self.stdout.write(f'  User: {user.username} ({user.email})')
        self.stdout.write(f'  Property: {property_item.property_name}')
        self.stdout.write(f'  Return Date: {return_date}')
        self.stdout.write(f'  Days Until Return: {days_until_return}')

        # Calculate reminder trigger date
        reminder_trigger_date = calculate_reminder_trigger_date(
            batch.request_date.date(),
            item.return_date
        )

        self.stdout.write(f'  Reminder Trigger Date: {reminder_trigger_date}')
        self.stdout.write(f'  Should trigger today? {reminder_trigger_date <= date.today()}')

        # Send the test email
        self.stdout.write(self.style.WARNING('\nSending test email...'))

        try:
            success = send_near_overdue_borrow_email(item)

            if success:
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Email sent successfully to {user.email}!')
                )
                self.stdout.write(self.style.WARNING('\nEmail Details:'))
                self.stdout.write(f'  To: {user.email}')
                self.stdout.write(
                    f'  Subject: Reminder: Your borrowed item \'{property_item.property_name}\' is due in {days_until_return} day(s)'
                )
                self.stdout.write(f'  Item: {property_item.property_name} (x{item.quantity})')
                self.stdout.write(f'  Due: {return_date.strftime("%B %d, %Y")}')
            else:
                self.stdout.write(
                    self.style.ERROR(f'✗ Failed to send email to {user.email}')
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Error sending email: {str(e)}')
            )

        self.stdout.write(self.style.WARNING('\n' + '='*60))
        self.stdout.write('Test batch created for reference:')
        self.stdout.write(f'  Batch ID: {batch.id}')
        self.stdout.write(f'  Item ID: {item.id}')
        self.stdout.write('You can delete this batch later if needed.')
        self.stdout.write('='*60)
