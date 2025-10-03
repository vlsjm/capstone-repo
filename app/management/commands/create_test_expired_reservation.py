from django.core.management.base import BaseCommand
from app.models import Reservation
from django.utils import timezone
from datetime import timedelta

class Command(BaseCommand):
    help = 'Create a test reservation that will be expired (for testing purposes)'
    
    def handle(self, *args, **options):
        from django.contrib.auth.models import User
        from app.models import Property
        
        # Get first user and property for testing
        try:
            user = User.objects.first()
            property_item = Property.objects.first()
            
            if not user or not property_item:
                self.stdout.write(self.style.ERROR('No users or properties found in the system'))
                return
            
            # Create a reservation with past dates
            past_date = timezone.now().date() - timedelta(days=5)
            very_past_date = timezone.now().date() - timedelta(days=10)
            
            reservation = Reservation.objects.create(
                user=user,
                item=property_item,
                quantity=1,
                needed_date=very_past_date,
                return_date=past_date,
                purpose="Test expired reservation",
                status='approved'  # Will be changed to expired by the update function
            )
            
            self.stdout.write(f'Created test reservation with ID {reservation.id}')
            self.stdout.write(f'Needed Date: {reservation.needed_date}')
            self.stdout.write(f'Return Date: {reservation.return_date}')
            self.stdout.write(f'Current Status: {reservation.status}')
            
            # Now run the status update to mark it as expired
            Reservation.check_and_update_reservations()
            
            # Refresh from database
            reservation.refresh_from_db()
            
            self.stdout.write(f'After update - Status: {reservation.status}')
            self.stdout.write(
                self.style.SUCCESS(f'Test reservation created and marked as expired: {reservation.id}')
            )
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating test reservation: {str(e)}'))