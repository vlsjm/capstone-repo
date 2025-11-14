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
    """
    AUTOMATED OVERDUE CHECK - Runs via scheduler every 2 hours
    
    This function does THREE critical tasks:
    1. Finds items that have passed their return_date
    2. Marks those items/batches as 'overdue'
    3. Sends SMS notifications to users (if not already notified)
    
    This ensures overdue detection happens automatically, not just when page is opened.
    """
    try:
        from app.models import BorrowRequestBatch
        
        logger.info("=" * 70)
        logger.info("SCHEDULER: Starting automated overdue check...")
        logger.info("=" * 70)
        
        # Call the model method that handles EVERYTHING:
        # - Marks batches as overdue
        # - Marks items as overdue  
        # - Sends SMS notifications
        # - Creates in-app notifications
        # - Prevents duplicate notifications
        BorrowRequestBatch.check_overdue_batches()
        
        logger.info("=" * 70)
        logger.info("SCHEDULER: Automated overdue check complete")
        logger.info("=" * 70)

    except Exception as e:
        logger.error(f"SCHEDULER ERROR in check_and_notify_overdue_items: {str(e)}", exc_info=True)


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

    # Schedule overdue checking and SMS notifications - run every 2 hours
    # This ensures items are checked and marked as overdue throughout the day
    # and SMS notifications are sent promptly
    scheduler.add_job(
        check_and_notify_overdue_items,
        "interval",
        hours=2,
        id="check_and_notify_overdue_items",
        name="Check and Notify Overdue Items (Every 2 Hours)",
        replace_existing=True,
    )
    logger.info("Scheduled task: check_and_notify_overdue_items (every 2 hours)")

    if not scheduler.running:
        scheduler.start()
        logger.info("Background scheduler started successfully")
    else:
        logger.info("Background scheduler is already running")
