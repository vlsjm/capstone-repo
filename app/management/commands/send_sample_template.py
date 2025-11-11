from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.utils import timezone
from datetime import date, timedelta


class Command(BaseCommand):
    help = 'Send a sample near-overdue email template to a specified email address'

    def add_arguments(self, parser):
        parser.add_argument(
            'email',
            type=str,
            help='Email address to send the sample template to'
        )

    def handle(self, *args, **options):
        email = options['email']
        
        self.stdout.write(self.style.WARNING(f'Sending sample near-overdue email to {email}...'))

        try:
            # Create sample context with all required fields
            sample_user = type('obj', (object,), {
                'first_name': 'John',
                'username': 'john_sample',
                'email': email
            })()
            
            sample_batch = type('obj', (object,), {'id': 999})()
            
            # Build absolute URL for dashboard
            import os
            site_url = os.getenv('SITE_URL', 'http://localhost:8000')
            dashboard_url = f"{site_url}/userpanel/dashboard/"
            
            context = {
                'user': sample_user,
                'batch_request': sample_batch,
                'property_name': 'Sample Item - Desktop Computer',
                'quantity': 2,
                'return_date': date.today() + timedelta(days=2),
                'days_until_return': 2,
                'dashboard_url': dashboard_url,
                'current_year': timezone.now().year,
            }

            # Render email template
            html_message = render_to_string('app/email/borrow_near_overdue_reminder.html', context)
            plain_message = strip_tags(html_message)

            # Send email
            send_mail(
                subject="Sample: Reminder: Your borrowed item 'Sample Item - Desktop Computer' is due in 2 day(s)",
                message=plain_message,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[email],
                html_message=html_message,
                fail_silently=False,
            )

            self.stdout.write(
                self.style.SUCCESS(f'✓ Sample email sent successfully to {email}!')
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Error sending email: {str(e)}')
            )
