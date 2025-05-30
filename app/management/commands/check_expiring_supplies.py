from django.core.management.base import BaseCommand
from app.models import Supply

class Command(BaseCommand):
    help = 'Check for supplies that are expiring soon or have expired and create notifications'

    def handle(self, *args, **kwargs):
        Supply.check_expiring_supplies()
        self.stdout.write(self.style.SUCCESS('Successfully checked for expiring supplies')) 