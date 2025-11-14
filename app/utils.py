import barcode
from barcode.writer import ImageWriter
from io import BytesIO
import base64
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.utils import timezone
from django.core.files.base import ContentFile
import logging
import requests
import os

logger = logging.getLogger(__name__)

def generate_barcode(code):
    """
    Generate a Code128 barcode and return it as a base64 encoded string.
    Deprecated: Use generate_barcode_image() for new implementations.
    """
    # Create barcode instance
    code128 = barcode.get_barcode_class('code128')
    
    # Configure barcode writer options for 1.5 inch width
    # 1.5 inch = 144 pixels at 96 DPI (standard screen DPI)
    # Module width controls the width of individual bars
    writer_options = {
        'module_width': 0.3,  # Width of individual bars in mm (larger = wider barcode)
        'module_height': 5.0,  # Height of bars in mm
        'quiet_zone': 3.0,  # Quiet zone on sides in mm
        'font_size': 1,  # Font size for text
        'text_distance': 5.0,  # Distance between barcode and text in mm (increased for balanced spacing)
        'dpi': 300,  # Higher DPI for better print quality
    }
    
    # Generate the barcode
    rv = BytesIO()
    code128(code, writer=ImageWriter()).write(rv, options=writer_options)
    
    # Convert to base64
    image_base64 = base64.b64encode(rv.getvalue()).decode()
    return f"data:image/png;base64,{image_base64}"


def generate_barcode_image(code):
    """
    Generate a Code128 barcode and return it as a ContentFile for ImageField.
    Returns a tuple: (filename, ContentFile)
    """
    # Create barcode instance
    code128 = barcode.get_barcode_class('code128')
    
    # Pad short codes to minimum 12 characters for consistent barcode width
    # This ensures all barcodes have similar bar thickness
    barcode_text = code
    if len(code) < 12:
        # Pad with spaces on the right to make all barcodes similar length
        barcode_text = code.ljust(12)
    
    # Configure barcode writer options for 1.5 inch width
    # 1.5 inch = 38.1 mm
    # Module width controls the width of individual bars
    writer_options = {
        'module_width': 0.3,  # Width of individual bars in mm
        'module_height': 15.0,  # Height of bars in mm (increased by 5mm)
        'quiet_zone': 3.0,  # Quiet zone on sides in mm
        'font_size': 10,  # Font size for text
        'text_distance': 5.0,  # Distance between barcode and text in mm
        'dpi': 300,  # Higher DPI for better print quality
    }
    
    # Generate the barcode with padded text
    rv = BytesIO()
    code128(barcode_text, writer=ImageWriter()).write(rv, options=writer_options)
    
    # Return as ContentFile with original filename (not padded)
    filename = f"{code}.png"
    return filename, ContentFile(rv.getvalue())
    return filename, ContentFile(rv.getvalue())



def send_batch_request_completion_email(batch_request, approved_items, rejected_items):
    """
    Send an email notification when a batch request is fully processed and ready for claiming.
    
    Args:
        batch_request: The SupplyRequestBatch instance
        approved_items: QuerySet of approved items
        rejected_items: QuerySet of rejected items
    """
    try:
        user = batch_request.user
        
        # Skip if user doesn't have an email
        if not user.email:
            logger.warning(f"User {user.username} doesn't have an email address. Skipping batch completion email notification.")
            return False
            
        # Prepare context for email template
        # Build absolute URL for dashboard
        site_url = os.getenv('SITE_URL', 'http://localhost:8000')
        dashboard_url = f"{site_url}/userpanel/dashboard/"
        
        context = {
            'user': user,
            'batch_request': batch_request,
            'approved_items': approved_items,
            'rejected_items': rejected_items,
            'has_approved_items': approved_items.exists(),
            'has_rejected_items': rejected_items.exists(),
            'total_approved': approved_items.count(),
            'total_rejected': rejected_items.count(),
            'total_items': batch_request.items.count(),
            'dashboard_url': dashboard_url,
            'current_year': timezone.now().year,
        }
        
        # Render email template
        html_message = render_to_string('app/email/batch_request_completed.html', context)
        plain_message = strip_tags(html_message)
        
        # Create subject based on batch status
        if approved_items.exists() and not rejected_items.exists():
            subject = f"Batch Request #{batch_request.id} - All Items Approved"
        elif approved_items.exists() and rejected_items.exists():
            subject = f"Batch Request #{batch_request.id} - Partially Approved"
        else:
            subject = f"Batch Request #{batch_request.id} - Request Rejected"
        
        # Send email
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Batch request completion email sent to {user.email} for batch #{batch_request.id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send batch completion email to {user.email}: {str(e)}")
        return False 

def send_borrow_batch_request_completion_email(batch_request, approved_items, rejected_items):
    """
    Send an email notification when a borrow batch request is fully processed and ready for claiming.
    
    Args:
        batch_request: The BorrowRequestBatch instance
        approved_items: QuerySet of approved items
        rejected_items: QuerySet of rejected items
    """
    try:
        user = batch_request.user
        
        # Skip if user doesn't have an email
        if not user.email:
            logger.warning(f"User {user.username} doesn't have an email address. Skipping borrow batch completion email notification.")
            return False
            
        # Prepare context for email template
        # Build absolute URL for dashboard
        site_url = os.getenv('SITE_URL', 'http://localhost:8000')
        dashboard_url = f"{site_url}/userpanel/dashboard/"
        
        context = {
            'user': user,
            'batch_request': batch_request,
            'approved_items': approved_items,
            'rejected_items': rejected_items,
            'has_approved_items': approved_items.exists(),
            'has_rejected_items': rejected_items.exists(),
            'total_approved': approved_items.count(),
            'total_rejected': rejected_items.count(),
            'total_items': batch_request.items.count(),
            'dashboard_url': dashboard_url,
            'current_year': timezone.now().year,
        }
        
        # Render email template
        html_message = render_to_string('app/email/borrow_batch_request_completed.html', context)
        plain_message = strip_tags(html_message)
        
        # Create subject based on batch status
        if approved_items.exists() and not rejected_items.exists():
            subject = f"Borrow Request #{batch_request.id} - All Items Approved"
        elif approved_items.exists() and rejected_items.exists():
            subject = f"Borrow Request #{batch_request.id} - Partially Approved"
        else:
            subject = f"Borrow Request #{batch_request.id} - Request Rejected"
        
        # Send email
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Borrow batch request completion email sent to {user.email} for batch #{batch_request.id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send borrow batch completion email to {user.email}: {str(e)}")
        return False 


def send_sms_alert(phone_number, message, sms_provider=0):
    """
    Send an SMS alert using the specified SMS provider.
    
    Args:
        phone_number (str): Recipient's phone number
        message (str): Message content
        sms_provider (int): SMS Provider (0 or 1) - default: 0
    
    Returns:
        tuple: (success: bool, response_data: dict or str)
    """
    try:
        # Get API token from environment or settings
        api_token = os.getenv('SMS_API_TOKEN') or getattr(settings, 'SMS_API_TOKEN', None)
        
        if not api_token:
            logger.warning("SMS API TOKEN not configured. Skipping SMS alert.")
            return False, "SMS API TOKEN not configured"
        
        # Get SMS API endpoint from environment or settings (configurable)
        # Default: iProgtech SMS API
        sms_url = os.getenv('SMS_API_ENDPOINT') or getattr(settings, 'SMS_API_ENDPOINT', 
                                                            'https://sms.iprogtech.com/api/v1/sms_messages')
        
        # Prepare request parameters (URL encoded for API)
        params = {
            'api_token': api_token,
            'phone_number': phone_number,
            'message': message
        }
        
        # Send SMS request
        response = requests.post(sms_url, params=params, timeout=10)
        
        if response.status_code == 200:
            logger.info(f"SMS alert sent successfully to {phone_number}")
            return True, response.json()
        else:
            logger.error(f"Failed to send SMS to {phone_number}. Status: {response.status_code}")
            return False, response.text
            
    except requests.exceptions.RequestException as e:
        logger.error(f"SMS request failed for {phone_number}: {str(e)}")
        return False, str(e)
    except Exception as e:
        logger.error(f"Unexpected error sending SMS to {phone_number}: {str(e)}")
        return False, str(e)


def send_overdue_borrow_sms(borrow_request):
    """
    Send an SMS reminder for an overdue borrow request.
    
    Args:
        borrow_request: The BorrowRequest instance
    
    Returns:
        bool: True if SMS was sent successfully, False otherwise
    """
    try:
        user = borrow_request.user
        
        # Get user phone number
        phone_number = None
        try:
            user_profile = user.userprofile
            phone_number = user_profile.phone
        except:
            logger.warning(f"User {user.username} doesn't have a phone number. Skipping SMS alert.")
            return False
        
        if not phone_number:
            logger.warning(f"User {user.username} has no phone number on file. Skipping SMS alert.")
            return False
        
        # Calculate days overdue
        from datetime import date
        days_overdue = (date.today() - borrow_request.return_date).days
        
        # Create SMS message
        message = (
            f"Hello {user.first_name or user.username},\n\n"
            f"This is a reminder that your borrow of {borrow_request.property.property_name} "
            f"(Qty: {borrow_request.quantity}) is OVERDUE.\n\n"
            f"Original return date: {borrow_request.return_date}\n"
            f"Days overdue: {days_overdue}\n\n"
            f"Please return the item at your earliest convenience.\n\n"
            f"Thank you,\nResource Hive Team"
        )
        
        # Send SMS
        success, response = send_sms_alert(phone_number, message)
        
        if success:
            logger.info(f"Overdue reminder SMS sent to {user.username} ({phone_number})")
        else:
            logger.error(f"Failed to send overdue reminder SMS to {user.username}: {response}")
        
        return success
        
    except Exception as e:
        logger.error(f"Error sending overdue SMS reminder: {str(e)}")
        return False


def calculate_reminder_trigger_date(borrow_date, return_date):
    """
    Calculate when to send a near-overdue reminder based on borrow duration.
    
    Uses a hybrid approach:
    - For SHORT-TERM borrows (1-2 days): Send reminder X hours before return date
    - For LONGER borrows: Calculate reminder based on percentage of borrow period remaining
    - Cap between MIN and MAX days to avoid too-early or too-late reminders
    
    Args:
        borrow_date: The date when the item was borrowed
        return_date: The date when the item should be returned
    
    Returns:
        datetime.datetime: The timezone-aware datetime on which the reminder should be sent
    """
    from datetime import timedelta, datetime, time
    from django.utils import timezone as tz
    from zoneinfo import ZoneInfo
    
    try:
        # Get the configured timezone
        local_tz = ZoneInfo(settings.TIME_ZONE)
        
        # Calculate total days borrowed
        days_borrowed = (return_date - borrow_date).days
        
        # Special handling for short-term borrows (1-2 days)
        if days_borrowed <= settings.BORROW_SHORT_TERM_DAYS:
            # For short-term borrows, send reminder X hours before return date
            # Assuming return date is end of day (23:59), subtract the notice hours
            return_datetime = datetime.combine(return_date, time(23, 59))
            # Make it timezone-aware
            return_datetime = return_datetime.replace(tzinfo=local_tz)
            reminder_trigger_datetime = return_datetime - timedelta(hours=settings.BORROW_SHORT_TERM_NOTICE_HOURS)
            
            logger.debug(
                f"SHORT-TERM borrow ({days_borrowed} days): "
                f"Reminder will trigger {settings.BORROW_SHORT_TERM_NOTICE_HOURS} hours before return "
                f"({reminder_trigger_datetime})"
            )
            
            return reminder_trigger_datetime
        
        # For longer borrows, use the percentage-based calculation
        # Calculate reminder days before return based on percentage of borrow period
        reminder_days_before = days_borrowed * settings.BORROW_REMINDER_PERCENTAGE
        
        # Apply min/max caps
        reminder_days_before = max(
            settings.BORROW_REMINDER_MIN_DAYS,
            min(settings.BORROW_REMINDER_MAX_DAYS, reminder_days_before)
        )
        
        # Calculate the trigger date (at start of day for longer borrows)
        reminder_trigger_date = return_date - timedelta(days=reminder_days_before)
        reminder_trigger_datetime = datetime.combine(reminder_trigger_date, time(0, 0))
        # Make it timezone-aware
        reminder_trigger_datetime = reminder_trigger_datetime.replace(tzinfo=local_tz)
        
        logger.debug(
            f"LONG-TERM borrow ({days_borrowed} days): "
            f"Reminder {reminder_days_before:.1f} days before return ({reminder_trigger_datetime.date()})"
        )
        
        return reminder_trigger_datetime
        
    except Exception as e:
        logger.error(f"Error calculating reminder trigger date: {str(e)}")
        return datetime.combine(return_date, time(0, 0)).replace(tzinfo=ZoneInfo(settings.TIME_ZONE))  # Fallback to return date if error



def send_near_overdue_borrow_email(borrow_request_item):
    """
    Send an email reminder for a borrow request item that is approaching its return date.
    
    Args:
        borrow_request_item: The BorrowRequestItem instance
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    try:
        from datetime import date, datetime, time
        
        user = borrow_request_item.batch_request.user
        
        # Skip if user doesn't have an email
        if not user.email:
            logger.warning(
                f"User {user.username} doesn't have an email address. "
                f"Skipping near-overdue reminder."
            )
            return False
        
        # Calculate days until return
        today = date.today()
        days_until_return = (borrow_request_item.return_date - today).days
        
        # Calculate hours until return for short-term borrows
        now = timezone.now()
        return_datetime = datetime.combine(borrow_request_item.return_date, time(23, 59))
        hours_until_return = (return_datetime - now).total_seconds() / 3600
        
        # Determine if this is a short-term borrow
        borrow_duration = (borrow_request_item.return_date - borrow_request_item.batch_request.request_date.date()).days
        is_short_term = borrow_duration <= settings.BORROW_SHORT_TERM_DAYS
        
        # Prepare context for email template
        # Build absolute URL for dashboard
        site_url = os.getenv('SITE_URL', 'http://localhost:8000')
        dashboard_url = f"{site_url}/userpanel/dashboard/"
        
        context = {
            'user': user,
            'batch_request': borrow_request_item.batch_request,
            'item': borrow_request_item,
            'property_name': borrow_request_item.property.property_name,
            'quantity': borrow_request_item.quantity,
            'return_date': borrow_request_item.return_date,
            'days_until_return': days_until_return,
            'hours_until_return': int(hours_until_return),
            'is_short_term': is_short_term,
            'dashboard_url': dashboard_url,
            'current_year': timezone.now().year,
        }
        
        # Render email template
        html_message = render_to_string('app/email/borrow_near_overdue_reminder.html', context)
        plain_message = strip_tags(html_message)
        
        # Create subject - show hours for short-term, days for longer borrows
        if is_short_term and hours_until_return < 24:
            subject = f"Reminder: Your borrowed item '{borrow_request_item.property.property_name}' is due in {int(hours_until_return)} hour(s)"
        else:
            subject = f"Reminder: Your borrowed item '{borrow_request_item.property.property_name}' is due in {days_until_return} day(s)"
        
        # Send email
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(
            f"Near-overdue reminder email sent to {user.email} for item "
            f"{borrow_request_item.property.property_name} (due {borrow_request_item.return_date}) "
            f"- {days_until_return} days / {int(hours_until_return)} hours remaining"
        )
        return True
        
    except Exception as e:
        logger.error(f"Failed to send near-overdue reminder email: {str(e)}")
        return False