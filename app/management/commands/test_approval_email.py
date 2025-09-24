from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from app.utils import send_supply_request_approval_email, send_batch_request_completion_email
from django.utils import timezone

class Command(BaseCommand):
    help = 'Test the supply request approval email functionality'

    def add_arguments(self, parser):
        parser.add_argument('--user-id', type=int, help='User ID to send test email to')
        parser.add_argument('--email', type=str, help='Email address to send test email to')
        parser.add_argument('--test-type', type=str, choices=['individual', 'batch'], default='individual',
                           help='Type of test email to send (individual or batch)')

    def handle(self, *args, **options):
        # Get user either by ID or create a test user with the provided email
        if options['user_id']:
            try:
                user = User.objects.get(id=options['user_id'])
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'User with ID {options["user_id"]} not found'))
                return
        elif options['email']:
            # Create or get a test user
            user, created = User.objects.get_or_create(
                email=options['email'],
                defaults={
                    'username': f'test_user_{options["email"].split("@")[0]}',
                    'first_name': 'Test',
                    'last_name': 'User'
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created test user: {user.username}'))
        else:
            self.stdout.write(self.style.ERROR('Please provide either --user-id or --email'))
            return

        # Update user email if not set
        if not user.email and options['email']:
            user.email = options['email']
            user.save()

        test_type = options['test_type']
        
        if test_type == 'individual':
            # Send individual approval test email
            result = send_supply_request_approval_email(
                user=user,
                supply_name='Test Supply Item',
                requested_quantity=5,
                approved_quantity=3,
                purpose='Testing email functionality',
                request_date=timezone.now(),
                approved_date=timezone.now(),
                batch_id=123,
                request_id=456,
                remarks='This is a test email to verify the approval notification system is working correctly.'
            )

            if result:
                self.stdout.write(self.style.SUCCESS(f'Individual approval test email sent successfully to {user.email}'))
            else:
                self.stdout.write(self.style.ERROR(f'Failed to send individual approval test email to {user.email}'))
                
        elif test_type == 'batch':
            # Create mock objects for batch completion email
            class MockSupply:
                def __init__(self, name):
                    self.supply_name = name
            
            class MockItem:
                def __init__(self, supply_name, quantity, approved_qty=None, remarks=''):
                    self.supply = MockSupply(supply_name)
                    self.quantity = quantity
                    self.approved_quantity = approved_qty or quantity
                    self.remarks = remarks
                    self.status = 'approved'
            
            class MockBatch:
                def __init__(self, user):
                    self.id = 789
                    self.user = user
                    self.purpose = 'Testing batch completion email functionality'
                    self.request_date = timezone.now()
                    self.approved_date = timezone.now()
                    self.status = 'for_claiming'
                    
                def get_status_display(self):
                    return 'For Claiming'
                    
                @property
                def items(self):
                    class MockManager:
                        def count(self):
                            return 3
                    return MockManager()
            
            # Create mock objects
            batch_request = MockBatch(user)
            
            approved_items = [
                MockItem('Office Supplies - Pens', 10, 10),
                MockItem('Computer Equipment - Mouse', 2, 1, 'Only 1 available'),
                MockItem('Cleaning Supplies - Paper Towels', 5, 5)
            ]
            rejected_items = [
                MockItem('Expensive Equipment - Laptop', 1, remarks='Budget constraints')
            ]
            
            # Create mock querysets
            class MockQuerySet:
                def __init__(self, items):
                    self._items = items
                
                def exists(self):
                    return len(self._items) > 0
                    
                def count(self):
                    return len(self._items)
                    
                def __iter__(self):
                    return iter(self._items)
            
            approved_qs = MockQuerySet(approved_items)
            rejected_qs = MockQuerySet(rejected_items)
            
            # Send batch completion test email
            result = send_batch_request_completion_email(batch_request, approved_qs, rejected_qs)
            
            if result:
                self.stdout.write(self.style.SUCCESS(f'Batch completion test email sent successfully to {user.email}'))
            else:
                self.stdout.write(self.style.ERROR(f'Failed to send batch completion test email to {user.email}'))
