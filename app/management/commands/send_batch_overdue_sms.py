from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from app.models import BorrowRequestItem
from app.utils import send_sms_alert
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Send SMS alerts for overdue batch borrow request items'

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

        # Get all overdue batch borrow items that are currently active (being borrowed) and not returned
        # Only include items with status 'active' or 'overdue' - exclude 'pending' and 'approved' that aren't active yet
        overdue_items = BorrowRequestItem.objects.filter(
            status__in=['active', 'overdue'],  # Only active/overdue items
            actual_return_date__isnull=True,
            return_date__lt=date.today()
        ).order_by('return_date')

        if days_threshold > 0:
            cutoff_date = date.today() - timedelta(days=days_threshold)
            overdue_items = overdue_items.filter(return_date__lte=cutoff_date)

        if not overdue_items.exists():
            self.stdout.write(self.style.SUCCESS('No overdue batch borrow items found.'))
            return

        self.stdout.write(
            self.style.WARNING(f'Found {overdue_items.count()} overdue batch borrow item(s)')
        )

        # Group items by user to avoid duplicate SMS
        items_by_user = {}
        for item in overdue_items:
            user = item.batch_request.user
            if user not in items_by_user:
                items_by_user[user] = []
            items_by_user[user].append(item)

        success_count = 0
        failure_count = 0
        skipped_count = 0

        for user, items in items_by_user.items():
            try:
                # Get user phone number
                phone_number = None
                try:
                    user_profile = user.userprofile
                    phone_number = user_profile.phone
                except:
                    pass

                if not phone_number:
                    skipped_count += 1
                    self.stdout.write(
                        self.style.WARNING(f"⊘ No phone number for {user.username}, skipping")
                    )
                    continue

                # Create comprehensive SMS message
                message = self._create_sms_message(user, items)

                # Send SMS alert
                try:
                    success, response = send_sms_alert(phone_number, message)

                    if success:
                        success_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(f"✓ SMS sent to {user.username} ({phone_number})")
                        )
                    else:
                        failure_count += 1
                        self.stdout.write(
                            self.style.ERROR(f"✗ Failed to send SMS to {user.username}: {response}")
                        )
                except Exception as e:
                    failure_count += 1
                    self.stdout.write(
                        self.style.ERROR(f"✗ Error sending SMS to {user.username}: {str(e)}")
                    )

            except Exception as e:
                failure_count += 1
                self.stdout.write(
                    self.style.ERROR(f"✗ Error processing user {user.username}: {str(e)}")
                )

        # Summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS(f'✓ Successful: {success_count}'))
        self.stdout.write(self.style.ERROR(f'✗ Failed: {failure_count}'))
        self.stdout.write(self.style.WARNING(f'⊘ Skipped (no phone): {skipped_count}'))
        self.stdout.write(self.style.WARNING(f'Total items processed: {len(items_by_user)}'))
        self.stdout.write('='*60)

    def _create_sms_message(self, user, items):
        """Create a formatted SMS message for overdue items."""
        user_name = user.first_name or user.username
        
        # If only one item, create personalized message
        if len(items) == 1:
            item = items[0]
            days_overdue = (date.today() - item.return_date).days
            
            message = (
                f"Hello {user_name},\n\n"
                f"This is a reminder that your borrow of {item.property.property_name} "
                f"(Qty: {item.quantity}) is OVERDUE.\n\n"
                f"Original return date: {item.return_date}\n"
                f"Days overdue: {days_overdue}\n\n"
                f"Please return the item at your earliest convenience.\n\n"
                f"Thank you,\nResource Hive Team"
            )
        else:
            # Multiple items - create summary message
            days_overdue_list = [(date.today() - item.return_date).days for item in items]
            max_days_overdue = max(days_overdue_list)
            
            item_summary = ", ".join([
                f"{item.property.property_name} (x{item.quantity})"
                for item in items[:3]
            ])
            
            if len(items) > 3:
                item_summary += f", and {len(items) - 3} more"
            
            message = (
                f"Hello {user_name},\n\n"
                f"You have {len(items)} OVERDUE item(s) from your borrow request(s):\n"
                f"{item_summary}\n\n"
                f"Most overdue: {max_days_overdue} days\n\n"
                f"Please return these items as soon as possible.\n\n"
                f"Thank you,\nResource Hive Team"
            )
        
        return message
