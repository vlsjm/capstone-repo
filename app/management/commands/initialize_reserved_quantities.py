"""
Management command to initialize reserved_quantity for all properties
based on existing pending/approved reservations and borrow requests.
"""
from django.core.management.base import BaseCommand
from django.db.models import Sum
from app.models import Property, ReservationItem, BorrowRequestItem


class Command(BaseCommand):
    help = 'Initialize reserved_quantity field for all properties based on existing pending/approved requests'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Initializing reserved quantities for properties...'))
        
        properties = Property.objects.all()
        total_properties = properties.count()
        updated_count = 0
        
        for property_obj in properties:
            # Calculate reserved from approved reservations (not pending)
            reservation_reserved = ReservationItem.objects.filter(
                property=property_obj,
                status='approved'
            ).aggregate(total=Sum('quantity'))['total'] or 0
            
            # Calculate reserved from approved borrow requests (not pending)
            borrow_reserved = BorrowRequestItem.objects.filter(
                property=property_obj,
                status='approved'
            ).aggregate(total=Sum('quantity'))['total'] or 0
            
            total_reserved = reservation_reserved + borrow_reserved
            
            if total_reserved > 0:
                property_obj.reserved_quantity = total_reserved
                property_obj.save(update_fields=['reserved_quantity'])
                updated_count += 1
                
                self.stdout.write(
                    f'  ✓ {property_obj.property_name} ({property_obj.property_number}): '
                    f'{total_reserved} units reserved '
                    f'(Reservations: {reservation_reserved}, Borrows: {borrow_reserved})'
                )
        
        self.stdout.write(self.style.SUCCESS(
            f'\nInitialization complete!'
            f'\n  Total properties: {total_properties}'
            f'\n  Properties with reservations: {updated_count}'
            f'\n  Properties without reservations: {total_properties - updated_count}'
        ))
