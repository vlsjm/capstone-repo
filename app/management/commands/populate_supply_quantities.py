from django.core.management.base import BaseCommand
from app.models import Supply, SupplyQuantity
import random


class Command(BaseCommand):
    help = 'Populate missing SupplyQuantity records for existing Supplies'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== POPULATING MISSING SUPPLY QUANTITIES ===\n'))
        
        # Find supplies without quantity info
        supplies_without_qty = []
        for supply in Supply.objects.all():
            try:
                supply.quantity_info
            except SupplyQuantity.DoesNotExist:
                supplies_without_qty.append(supply)
        
        self.stdout.write(f'Found {len(supplies_without_qty)} supplies without quantity information\n')
        self.stdout.write(f'Creating quantity records...')
        
        created_count = 0
        for supply in supplies_without_qty:
            try:
                current_qty = random.randint(5, 500)
                SupplyQuantity.objects.create(
                    supply=supply,
                    current_quantity=current_qty,
                    reserved_quantity=random.randint(0, current_qty // 2),
                    minimum_threshold=random.randint(5, 50),
                )
                created_count += 1
                
                if created_count % 50 == 0:
                    self.stdout.write(f'  [OK] Created {created_count}/{len(supplies_without_qty)} quantity records')
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  [ERROR] Error creating quantity for supply {supply.id}: {str(e)}'))
        
        self.stdout.write(self.style.SUCCESS(f'\n[OK] Created {created_count} supply quantity records'))
        
        # Summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write('UPDATED SUPPLY STATISTICS')
        self.stdout.write('='*60)
        
        supply_qty = SupplyQuantity.objects.all()
        total_qty = sum(sq.current_quantity for sq in supply_qty)
        total_reserved = sum(sq.reserved_quantity for sq in supply_qty)
        total_available = sum(sq.available_quantity for sq in supply_qty)
        
        self.stdout.write(f'  Total Supplies: {Supply.objects.count()}')
        self.stdout.write(f'  Total Quantity in Stock: {total_qty} units')
        self.stdout.write(f'  Total Reserved Quantity: {total_reserved} units')
        self.stdout.write(f'  Total Available Quantity: {total_available} units')
        self.stdout.write('='*60 + '\n')
        
        self.stdout.write(self.style.SUCCESS('[OK] Supply quantity population completed!'))
