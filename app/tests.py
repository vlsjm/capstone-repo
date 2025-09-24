from django.test import TestCase
from django.contrib.auth.models import User
from django.core import mail
from django.utils import timezone
from .utils import send_supply_request_approval_email, send_batch_request_completion_email

class EmailNotificationTestCase(TestCase):
    def setUp(self):
        """Set up test data"""
        # Create a test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            first_name='Test',
            last_name='User'
        )

    def test_send_approval_email_basic(self):
        """Test basic email sending functionality"""
        result = send_supply_request_approval_email(
            user=self.user,
            supply_name='Test Supply',
            requested_quantity=5,
            purpose='Testing',
            request_date=timezone.now(),
            approved_date=timezone.now(),
            request_id=1
        )
        
        # Check that email was sent
        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        
        # Check email details
        email = mail.outbox[0]
        self.assertIn('Test Supply', email.subject)
        self.assertIn('test@example.com', email.to)
        self.assertIn('approved', email.subject.lower())

    def test_send_approval_email_with_batch(self):
        """Test email sending for batch requests"""
        result = send_supply_request_approval_email(
            user=self.user,
            supply_name='Test Supply',
            requested_quantity=5,
            approved_quantity=3,
            purpose='Testing batch request',
            request_date=timezone.now(),
            approved_date=timezone.now(),
            batch_id=123,
            remarks='Partial approval'
        )
        
        # Check that email was sent
        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        
        # Check email details
        email = mail.outbox[0]
        self.assertIn('Batch #123', email.subject)
        self.assertIn('test@example.com', email.to)

    def test_send_approval_email_no_email_address(self):
        """Test handling of users without email addresses"""
        # Create user without email
        user_no_email = User.objects.create_user(
            username='noemail',
            email='',  # No email
            first_name='No',
            last_name='Email'
        )
        
        result = send_supply_request_approval_email(
            user=user_no_email,
            supply_name='Test Supply',
            requested_quantity=5,
            purpose='Testing',
            request_date=timezone.now(),
            approved_date=timezone.now(),
            request_id=1
        )
        
        # Should return False and not send email
        self.assertFalse(result)
        self.assertEqual(len(mail.outbox), 0)

    def test_batch_completion_email_all_approved(self):
        """Test batch completion email when all items are approved"""
        from .models import SupplyRequestBatch, SupplyRequestItem, Supply, SupplyCategory
        
        # Create minimal test data for batch completion email
        class MockSupply:
            def __init__(self, name):
                self.supply_name = name
        
        class MockItem:
            def __init__(self, supply_name, quantity, approved_qty=None, remarks=''):
                self.supply = MockSupply(supply_name)
                self.quantity = quantity
                self.approved_quantity = approved_qty or quantity
                self.remarks = remarks
                self.status = 'approved'
        
        class MockBatch:
            def __init__(self, user):
                self.id = 123
                self.user = user
                self.purpose = 'Test batch request'
                self.request_date = timezone.now()
                self.approved_date = timezone.now()
                self.status = 'for_claiming'
                
            def get_status_display(self):
                return 'For Claiming'
                
            @property
            def items(self):
                # Mock items property for template access
                class MockManager:
                    def count(self):
                        return 2
                return MockManager()
        
        # Create mock objects
        batch_request = MockBatch(self.user)
        
        approved_items = [
            MockItem('Item 1', 5, 5),
            MockItem('Item 2', 3, 2, 'Partial approval')
        ]
        rejected_items = []
        
        # Create mock querysets
        class MockQuerySet:
            def __init__(self, items):
                self._items = items
            
            def exists(self):
                return len(self._items) > 0
                
            def count(self):
                return len(self._items)
                
            def __iter__(self):
                return iter(self._items)
        
        approved_qs = MockQuerySet(approved_items)
        rejected_qs = MockQuerySet(rejected_items)
        
        # Test the batch completion email function
        result = send_batch_request_completion_email(batch_request, approved_qs, rejected_qs)
        
        # Check that email was sent
        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        
        # Check email details
        email = mail.outbox[0]
        self.assertIn('Batch Request #123', email.subject)
        self.assertIn('All Items Approved', email.subject)
        self.assertIn('test@example.com', email.to)
