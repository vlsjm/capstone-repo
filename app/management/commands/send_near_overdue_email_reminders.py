from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date
from app.models import BorrowRequestItem
from app.utils import calculate_reminder_trigger_date, send_near_overdue_borrow_email
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Send email reminders for borrow request items that are approaching their return date'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force send email reminders even if already notified'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be sent without actually sending'
        )

    def handle(self, *args, **options):
        force_send = options['force']
        dry_run = options['dry_run']

        # Get all active borrow items that haven't been returned
        active_items = BorrowRequestItem.objects.filter(
            status__in=['active'],
            actual_return_date__isnull=True,
            batch_request__status__in=['active', 'overdue']
        ).select_related('batch_request', 'batch_request__user', 'property')

        if not active_items.exists():
            self.stdout.write(self.style.SUCCESS('No active borrow items found.'))
            return

        self.stdout.write(
            self.style.WARNING(f'Found {active_items.count()} active borrow item(s)')
        )

        # Filter items that need reminders
        items_needing_reminder = []
        now = timezone.now()
        today = now.date()

        for item in active_items:
            # Calculate when reminder should be sent (returns datetime)
            reminder_trigger_datetime = calculate_reminder_trigger_date(
                item.batch_request.request_date.date(),
                item.return_date
            )

            # Check if current time has passed trigger datetime (but before return date)
            if now >= reminder_trigger_datetime and today <= item.return_date:
                items_needing_reminder.append(item)

        if not items_needing_reminder:
            self.stdout.write(self.style.SUCCESS('No items need reminder at this time.'))
            return

        self.stdout.write(
            self.style.WARNING(f'Found {len(items_needing_reminder)} item(s) needing reminder')
        )

        if dry_run:
            self.stdout.write(self.style.WARNING('\n=== DRY RUN MODE ===\n'))

        success_count = 0
        failure_count = 0

        for item in items_needing_reminder:
            try:
                days_until_return = (item.return_date - today).days
                user = item.batch_request.user
                
                # Calculate hours for short-term borrows
                from datetime import datetime, time
                return_datetime = datetime.combine(item.return_date, time(23, 59))
                hours_until_return = (return_datetime - now).total_seconds() / 3600

                self.stdout.write(
                    f"Processing: {user.username} - "
                    f"{item.property.property_name} "
                    f"({days_until_return} days / {hours_until_return:.1f} hours until return)"
                )

                if dry_run:
                    self.stdout.write(
                        self.style.WARNING(
                            f"[DRY RUN] Would send reminder email to {user.email}"
                        )
                    )
                    success_count += 1
                else:
                    # Send email reminder
                    success = send_near_overdue_borrow_email(item)

                    if success:
                        success_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(f"✓ Email sent to {user.email}")
                        )
                    else:
                        failure_count += 1
                        self.stdout.write(
                            self.style.ERROR(f"✗ Failed to send email to {user.email}")
                        )

            except Exception as e:
                failure_count += 1
                self.stdout.write(
                    self.style.ERROR(f"✗ Error processing {user.username}: {str(e)}")
                )

        # Summary
        self.stdout.write('\n' + '='*50)
        if dry_run:
            self.stdout.write(self.style.WARNING('[DRY RUN] Would send:'))
        self.stdout.write(self.style.SUCCESS(f'Successful: {success_count}'))
        if not dry_run:
            self.stdout.write(self.style.ERROR(f'Failed: {failure_count}'))
        self.stdout.write(self.style.WARNING(f'Total: {success_count + failure_count}'))
        self.stdout.write('='*50)
