"""
Scheduler for periodic tasks like sending near-overdue email reminders and overdue SMS alerts.
"""
import logging
from datetime import date
from django.conf import settings
from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore
from django_apscheduler.util import close_old_connections

logger = logging.getLogger(__name__)


def send_near_overdue_reminders():
    """Send email reminders for items approaching their return date."""
    # Don't close connections in test mode - just run directly
    
    try:
        from app.models import BorrowRequestBatch
        
        logger.info("Starting near-overdue email reminder check via scheduler...")
        BorrowRequestBatch.check_near_overdue_items()
        logger.info("Near-overdue email reminder check complete")

    except Exception as e:
        logger.error(f"Error in send_near_overdue_reminders task: {str(e)}", exc_info=True)


def check_and_notify_overdue_items():
    """Check for overdue items and send SMS alerts if not already notified."""
    # Don't close connections in test mode - just run directly
    
    try:
        from app.models import BorrowRequestItem
        from app.utils import send_sms_alert
        from zoneinfo import ZoneInfo
        
        logger.info("Starting overdue item check and SMS notification...")
        
        local_tz = ZoneInfo(settings.TIME_ZONE)
        today = date.today()
        
        # Find overdue items that haven't been notified yet
        overdue_items = BorrowRequestItem.objects.filter(
            status='overdue',
            actual_return_date__isnull=True,
            overdue_notified=False,
            return_date__lt=today
        ).select_related('batch_request', 'batch_request__user', 'property')
        
        if not overdue_items.exists():
            logger.debug("No unnotified overdue items found")
            return
        
        logger.info(f"Found {overdue_items.count()} unnotified overdue item(s)")
        
        success_count = 0
        failure_count = 0
        
        # Group by user to avoid duplicate SMS
        items_by_user = {}
        for item in overdue_items:
            user = item.batch_request.user
            if user not in items_by_user:
                items_by_user[user] = []
            items_by_user[user].append(item)
        
        for user, user_items in items_by_user.items():
            try:
                # Get user phone number
                phone_number = None
                try:
                    user_profile = user.userprofile
                    phone_number = user_profile.phone
                except:
                    logger.warning(f"User {user.username} doesn't have a phone number. Skipping SMS.")
                    continue
                
                if not phone_number:
                    logger.warning(f"User {user.username} has no phone number on file. Skipping SMS.")
                    continue
                
                # Create comprehensive SMS message for all overdue items
                user_name = user.first_name or user.username
                item_count = len(user_items)
                
                # Calculate days overdue
                days_overdue_list = [(today - item.return_date).days for item in user_items]
                max_days_overdue = max(days_overdue_list) if days_overdue_list else 0
                
                # Create item summary
                item_summary = ", ".join([
                    f"{item.property.property_name} (x{item.quantity})"
                    for item in user_items[:3]
                ])
                
                if len(user_items) > 3:
                    item_summary += f", and {len(user_items) - 3} more"
                
                message = (
                    f"Hello {user_name},\n\n"
                    f"URGENT: You have {item_count} OVERDUE item(s):\n"
                    f"{item_summary}\n\n"
                    f"Most overdue: {max_days_overdue} days\n\n"
                    f"Please return these items IMMEDIATELY.\n\n"
                    f"Thank you,\nResource Hive Team"
                )
                
                logger.info(f"\n{'='*60}\nOVERDUE SMS TO {phone_number}:\n{'='*60}\n{message}\n{'='*60}")
                
                # Send SMS
                success, response = send_sms_alert(phone_number, message)
                
                if success:
                    # Mark all items as notified
                    for item in user_items:
                        item.overdue_notified = True
                        item.save(update_fields=['overdue_notified'])
                    success_count += 1
                    logger.info(f"[OK] Overdue SMS sent to {user.username} ({phone_number}) for {item_count} item(s)")
                else:
                    failure_count += 1
                    logger.error(f"[FAIL] Failed to send overdue SMS to {user.username}: {response}")
            
            except Exception as e:
                failure_count += 1
                logger.error(f"Error sending overdue SMS to {user.username}: {str(e)}")
        
        if success_count + failure_count > 0:
            logger.info(f"Overdue notification check complete: {success_count} sent, {failure_count} failed")

    except Exception as e:
        logger.error(f"Error in check_and_notify_overdue_items task: {str(e)}", exc_info=True)


def start_scheduler():
    """Initialize and start the background scheduler."""
    scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)
    scheduler.add_jobstore(DjangoJobStore(), "default")

    # Schedule near-overdue email reminders - run every 6 hours
    scheduler.add_job(
        send_near_overdue_reminders,
        "interval",
        hours=6,
        id="send_near_overdue_reminders",
        name="Send Near-Overdue Email Reminders",
        replace_existing=True,
    )
    logger.info("Scheduled task: send_near_overdue_reminders (every 6 hours)")

    # Schedule overdue SMS notifications - run multiple times daily
    # 8 AM, 12 PM (noon), 4 PM, 8 PM to catch items that become overdue throughout the day
    for hour in [8, 12, 16, 20]:
        scheduler.add_job(
            check_and_notify_overdue_items,
            "cron",
            hour=hour,
            minute=0,
            id=f"check_and_notify_overdue_items_{hour}",
            name=f"Check and Notify Overdue Items ({hour}:00)",
            replace_existing=True,
        )
    logger.info("Scheduled task: check_and_notify_overdue_items (4 times daily: 8 AM, 12 PM, 4 PM, 8 PM)")

    if not scheduler.running:
        scheduler.start()
        logger.info("Background scheduler started successfully")
    else:
        logger.info("Background scheduler is already running")
