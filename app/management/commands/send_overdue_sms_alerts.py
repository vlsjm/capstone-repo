from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from app.models import BorrowRequest
from app.utils import send_overdue_borrow_sms
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Send SMS alerts for overdue borrow requests'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=0,
            help='Number of days overdue to trigger alert (default: 0 = any overdue)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force send SMS even if already notified'
        )

    def handle(self, *args, **options):
        days_threshold = options['days']
        force_send = options['force']

        # Get all overdue borrow requests that haven't been returned
        overdue_requests = BorrowRequest.objects.filter(
            status__in=['approved', 'overdue'],
            actual_return_date__isnull=True,
            return_date__lt=date.today()
        ).order_by('return_date')

        if days_threshold > 0:
            cutoff_date = date.today() - timedelta(days=days_threshold)
            overdue_requests = overdue_requests.filter(return_date__lte=cutoff_date)

        if not overdue_requests.exists():
            self.stdout.write(self.style.SUCCESS('No overdue borrow requests found.'))
            return

        self.stdout.write(
            self.style.WARNING(f'Found {overdue_requests.count()} overdue borrow request(s)')
        )

        success_count = 0
        failure_count = 0

        for borrow_request in overdue_requests:
            try:
                # Calculate days overdue
                days_overdue = (date.today() - borrow_request.return_date).days
                
                self.stdout.write(
                    f"Processing: {borrow_request.user.username} - "
                    f"{borrow_request.property.property_name} "
                    f"({days_overdue} days overdue)"
                )

                # Send SMS alert
                success = send_overdue_borrow_sms(borrow_request)

                if success:
                    success_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f"✓ SMS sent to {borrow_request.user.username}")
                    )
                else:
                    failure_count += 1
                    self.stdout.write(
                        self.style.ERROR(f"✗ Failed to send SMS to {borrow_request.user.username}")
                    )

            except Exception as e:
                failure_count += 1
                self.stdout.write(
                    self.style.ERROR(f"✗ Error processing {borrow_request.user.username}: {str(e)}")
                )

        # Summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS(f'Successful: {success_count}'))
        self.stdout.write(self.style.ERROR(f'Failed: {failure_count}'))
        self.stdout.write(self.style.WARNING(f'Total: {success_count + failure_count}'))
        self.stdout.write('='*50)
