from django.core.management.base import BaseCommand
from app.models import Reservation

class Command(BaseCommand):
    help = 'Update reservation statuses based on dates (mark expired, activate, complete)'
    
    def handle(self, *args, **options):
        self.stdout.write('Checking and updating reservation statuses...')
        
        # Run the reservation status update
        Reservation.check_and_update_reservations()
        
        self.stdout.write(
            self.style.SUCCESS('Successfully updated reservation statuses')
        )