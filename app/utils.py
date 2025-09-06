import barcode
from barcode.writer import ImageWriter
from io import BytesIO
import base64
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

def generate_barcode(code):
    """Generate a Code128 barcode and return it as a base64 encoded string."""
    # Create barcode instance
    code128 = barcode.get_barcode_class('code128')
    
    # Generate the barcode
    rv = BytesIO()
    code128(code, writer=ImageWriter()).write(rv)
    
    # Convert to base64
    image_base64 = base64.b64encode(rv.getvalue()).decode()
    return f"data:image/png;base64,{image_base64}"



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
            'dashboard_url': "http://localhost:8000/userpanel/dashboard/",
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
            'dashboard_url': "http://localhost:8000/userpanel/dashboard/",
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