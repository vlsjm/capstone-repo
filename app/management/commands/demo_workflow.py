from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date, timedelta
from app.models import Reservation, Property, BorrowRequestBatch, BorrowRequestItem, Notification


class Command(BaseCommand):
    help = 'Demonstrate the complete reservation-to-borrowing workflow'

    def add_arguments(self, parser):
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='Clean up test data after demonstration',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== RESERVATION-TO-BORROWING WORKFLOW DEMONSTRATION ==='))
        
        # Get test user and property
        test_user = User.objects.filter(username='johnm').first() or User.objects.first()
        test_property = Property.objects.filter(quantity__gt=0).first()
        
        if not test_user or not test_property:
            self.stdout.write(self.style.ERROR('Need at least one user and one property with available quantity'))
            return
            
        self.stdout.write(f'\n1. CREATING RESERVATION')
        self.stdout.write(f'   User: {test_user.username}')
        self.stdout.write(f'   Item: {test_property.property_name} (Available: {test_property.quantity})')
        
        # Create reservation for tomorrow (future needed_date)
        tomorrow = timezone.now().date() + timedelta(days=1)
        next_week = tomorrow + timedelta(days=7)
        
        # Create the reservation
        reservation = Reservation.objects.create(
            user=test_user,
            item=test_property,
            quantity=1,
            needed_date=tomorrow,
            return_date=next_week,
            purpose='Workflow demonstration - reserve for tomorrow',
            status='pending'
        )
        
        self.stdout.write(f'   ✓ Created Reservation #{reservation.id}')
        self.stdout.write(f'   ✓ Status: {reservation.status}')
        self.stdout.write(f'   ✓ Period: {reservation.needed_date} to {reservation.return_date}')
        
        self.stdout.write(f'\n2. ADMIN APPROVES RESERVATION')
        reservation.status = 'approved'
        reservation.approved_date = timezone.now()
        reservation.save()
        self.stdout.write(f'   ✓ Reservation #{reservation.id} approved')
        
        self.stdout.write(f'\n3. SIMULATING NEEDED_DATE ARRIVAL (changing needed_date to today)')
        # Simulate that the needed_date has arrived by changing it to today
        reservation.needed_date = timezone.now().date()
        reservation.save()
        
        self.stdout.write(f'\n4. RUNNING AUTOMATIC CHECK (simulates daily cron job)')
        # Run the automatic check
        Reservation.check_and_update_reservations()
        
        # Refresh objects
        reservation.refresh_from_db()
        
        self.stdout.write(f'\n5. CHECKING RESULTS')
        self.stdout.write(f'   Reservation Status: {reservation.status}')
        
        if reservation.generated_borrow_batch:
            borrow_batch = reservation.generated_borrow_batch
            self.stdout.write(f'   ✓ Auto-generated Borrow Request #{borrow_batch.id}')
            self.stdout.write(f'   ✓ Borrow Batch Status: {borrow_batch.status}')
            self.stdout.write(f'   ✓ Borrow Batch Purpose: {borrow_batch.purpose}')
            
            # Show borrow request items
            for item in borrow_batch.items.all():
                self.stdout.write(f'   ✓ Item: {item.property.property_name} (x{item.quantity}) - Status: {item.status}')
                
        self.stdout.write(f'\n6. WORKFLOW SUMMARY')
        self.stdout.write(f'   📅 Day 1: User submits reservation → Status: pending')
        self.stdout.write(f'   👨‍💼 Day 2: Admin approves → Status: approved')
        self.stdout.write(f'   🤖 Day X (needed_date): System auto-creates borrow request → Status: active')
        self.stdout.write(f'   🏢 User visits office: Admin marks borrow request as active (items claimed)')
        self.stdout.write(f'   🔄 User returns items: Admin marks as returned')
        
        # Show the current state that admin would see
        self.stdout.write(f'\n7. ADMIN DASHBOARD VIEW')
        self.stdout.write(f'   📋 Reservations Tab:')
        self.stdout.write(f'      - Reservation #{reservation.id}: Status = {reservation.status}')
        self.stdout.write(f'   📦 Borrow Requests Tab:')
        if reservation.generated_borrow_batch:
            self.stdout.write(f'      - Borrow Request #{reservation.generated_borrow_batch.id}: Status = {reservation.generated_borrow_batch.status}')
            self.stdout.write(f'      - Action Available: "Mark as Active" (when user picks up items)')
        
        # Show recent notifications
        recent_notifications = Notification.objects.filter(
            timestamp__gte=timezone.now() - timedelta(minutes=5)
        ).order_by('-timestamp')[:3]
        
        if recent_notifications:
            self.stdout.write(f'\n8. NOTIFICATIONS SENT')
            for notification in recent_notifications:
                self.stdout.write(f'   📧 To {notification.user.username}: {notification.message}')
        
        # Cleanup option
        if options['cleanup']:
            self.stdout.write(f'\n🧹 CLEANING UP TEST DATA')
            if reservation.generated_borrow_batch:
                borrow_id = reservation.generated_borrow_batch.id
                reservation.generated_borrow_batch.delete()
                self.stdout.write(f'   ✓ Deleted Borrow Request #{borrow_id}')
            reservation.delete()
            self.stdout.write(f'   ✓ Deleted Reservation #{reservation.id}')
            
            # Clean up notifications
            Notification.objects.filter(
                timestamp__gte=timezone.now() - timedelta(minutes=5)
            ).delete()
            self.stdout.write(f'   ✓ Cleaned up test notifications')
        
        self.stdout.write(f'\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('✨ WORKFLOW DEMONSTRATION COMPLETE ✨'))
        
        if not options['cleanup']:
            self.stdout.write(f'\n💡 Tip: Run with --cleanup to remove test data')
            self.stdout.write(f'   Example: python manage.py demo_workflow --cleanup')