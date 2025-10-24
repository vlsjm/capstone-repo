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