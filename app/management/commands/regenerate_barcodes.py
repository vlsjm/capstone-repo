from django.core.management.base import BaseCommand
from app.models import Supply, Property
from app.utils import generate_barcode_image


class Command(BaseCommand):
    help = 'Regenerate barcodes for all supplies and properties'

    def handle(self, *args, **kwargs):
        self.stdout.write('Regenerating barcodes...\n')
        
        # Regenerate Supply barcodes
        supplies_updated = 0
        for supply in Supply.objects.all():
            barcode_text = f"SUP-{supply.id}"
            
            # Update barcode text
            supply.barcode = barcode_text
            
            # Generate and save barcode image
            filename, content = generate_barcode_image(barcode_text)
            supply.barcode_image.save(filename, content, save=False)
            
            # Save without triggering the save override
            Supply.objects.filter(pk=supply.pk).update(barcode=barcode_text)
            supply.save(update_fields=['barcode_image'])
            
            supplies_updated += 1
            if supplies_updated % 50 == 0:
                self.stdout.write(f'  Processed {supplies_updated} supplies...')
        
        self.stdout.write(self.style.SUCCESS(f'✓ Updated {supplies_updated} supplies'))
        
        # Regenerate Property barcodes
        properties_updated = 0
        for prop in Property.objects.all():
            # Use property_number if available, otherwise use ID
            barcode_text = prop.property_number if prop.property_number else f"PROP-{prop.id}"
            
            # Update barcode text
            prop.barcode = barcode_text
            
            # Generate and save barcode image
            filename, content = generate_barcode_image(barcode_text)
            prop.barcode_image.save(filename, content, save=False)
            
            # Save without triggering the save override
            Property.objects.filter(pk=prop.pk).update(barcode=barcode_text)
            prop.save(update_fields=['barcode_image'])
            
            properties_updated += 1
            if properties_updated % 50 == 0:
                self.stdout.write(f'  Processed {properties_updated} properties...')
        
        self.stdout.write(self.style.SUCCESS(f'✓ Updated {properties_updated} properties'))
        
        self.stdout.write(self.style.SUCCESS(f'\n✅ Successfully regenerated all barcodes!'))
