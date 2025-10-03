from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date, timedelta
from app.models import Reservation, Property, BorrowRequestBatch, BorrowRequestItem, Notification


class Command(BaseCommand):
    help = 'Test the automatic reservation-to-borrowing workflow'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Testing automatic reservation-to-borrowing workflow...'))
        
        # Get a test user (or create one)
        try:
            test_user = User.objects.get(username='johnm')
        except User.DoesNotExist:
            test_user = User.objects.first()
            
        if not test_user:
            self.stdout.write(self.style.ERROR('No users found in the system. Please create a user first.'))
            return
            
        # Get a test property (or create one)
        try:
            test_property = Property.objects.filter(quantity__gt=0).first()
        except Property.DoesNotExist:
            test_property = None
            
        if not test_property:
            self.stdout.write(self.style.ERROR('No properties with available quantity found. Please add some properties first.'))
            return
            
        # Create a test reservation that should trigger the auto-workflow
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)  # needed_date in the past to trigger immediate workflow
        future_date = today + timedelta(days=7)  # return_date in the future
        
        # Check if we already have a test reservation
        existing_reservation = Reservation.objects.filter(
            user=test_user,
            item=test_property,
            purpose__icontains='Auto-workflow test'
        ).first()
        
        if existing_reservation:
            self.stdout.write(f'Using existing test reservation #{existing_reservation.id}')
            test_reservation = existing_reservation
        else:
            # Create new test reservation
            test_reservation = Reservation.objects.create(
                user=test_user,
                item=test_property,
                quantity=1,
                needed_date=yesterday,
                return_date=future_date,
                purpose='Auto-workflow test reservation',
                status='pending'
            )
            self.stdout.write(f'Created test reservation #{test_reservation.id}')
        
        # Show initial state
        self.stdout.write(f'\nInitial state:')
        self.stdout.write(f'Reservation #{test_reservation.id} status: {test_reservation.status}')
        self.stdout.write(f'Property {test_property.property_name} quantity: {test_property.quantity}')
        
        # Manually approve the reservation (simulating admin approval)
        if test_reservation.status == 'pending':
            test_reservation.status = 'approved'
            test_reservation.approved_date = timezone.now()
            test_reservation.save()
            self.stdout.write(f'Approved reservation #{test_reservation.id}')
        
        # Run the automatic check
        self.stdout.write(f'\nRunning automatic reservation check...')
        Reservation.check_and_update_reservations()
        
        # Refresh the reservation object
        test_reservation.refresh_from_db()
        
        # Check results
        self.stdout.write(f'\nAfter automatic check:')
        self.stdout.write(f'Reservation #{test_reservation.id} status: {test_reservation.status}')
        
        if test_reservation.generated_borrow_batch:
            borrow_batch = test_reservation.generated_borrow_batch
            self.stdout.write(f'Generated Borrow Request Batch #{borrow_batch.id}')
            self.stdout.write(f'Borrow Batch status: {borrow_batch.status}')
            
            # Check borrow request items
            borrow_items = borrow_batch.items.all()
            for item in borrow_items:
                self.stdout.write(f'  - Item: {item.property.property_name} (x{item.quantity}) - Status: {item.status}')
                
            # Check notifications
            recent_notifications = Notification.objects.filter(
                timestamp__gte=timezone.now() - timedelta(minutes=5)
            ).order_by('-timestamp')[:5]
            
            self.stdout.write(f'\nRecent notifications:')
            for notification in recent_notifications:
                self.stdout.write(f'  - To {notification.user.username}: {notification.message}')
                
        else:
            self.stdout.write('No borrow request batch was generated')
            
        # Show summary
        self.stdout.write(f'\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('Workflow test completed!'))
        
        if test_reservation.status == 'active' and test_reservation.generated_borrow_batch:
            self.stdout.write(self.style.SUCCESS('✓ Reservation successfully converted to borrow request'))
            self.stdout.write(f'✓ Borrow Request #{test_reservation.generated_borrow_batch.id} created with status: {test_reservation.generated_borrow_batch.status}')
        else:
            self.stdout.write(self.style.WARNING('! Workflow did not complete as expected'))
            self.stdout.write(f'  Reservation status: {test_reservation.status}')
            self.stdout.write(f'  Generated borrow batch: {test_reservation.generated_borrow_batch}')