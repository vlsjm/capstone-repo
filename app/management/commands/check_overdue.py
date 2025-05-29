from django.core.management.base import BaseCommand
from app.models import BorrowRequest
from django.utils import timezone

class Command(BaseCommand):
    help = 'Check for overdue borrowed items and update their status'

    def handle(self, *args, **kwargs):
        self.stdout.write('Checking for overdue items...')
        
        # Call the check_overdue_items class method
        BorrowRequest.check_overdue_items()
        
        self.stdout.write(self.style.SUCCESS('Successfully checked for overdue items')) 