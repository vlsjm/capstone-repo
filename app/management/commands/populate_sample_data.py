from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from app.models import (
    Supply, SupplyCategory, SupplySubcategory, SupplyQuantity,
    Property, PropertyCategory, Department
)
import random


class Command(BaseCommand):
    help = 'Populate Supply and Property tables with realistic sample data for testing system capabilities and performance'

    def add_arguments(self, parser):
        parser.add_argument(
            '--supplies',
            type=int,
            default=50,
            help='Number of supply records to create (default: 50)',
        )
        parser.add_argument(
            '--properties',
            type=int,
            default=50,
            help='Number of property records to create (default: 50)',
        )
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='Delete all existing supply and property data before populating (REQUIRES manual DB cleanup)',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== POPULATING SAMPLE DATA ===\n'))
        
        # Note about cleanup
        if options['cleanup']:
            self.stdout.write(self.style.WARNING('NOTE: The --cleanup flag requires manual database cleanup due to sequence constraints.'))
            self.stdout.write(self.style.WARNING('To fully reset: Run "python manage.py dbshell" and execute:'))
            self.stdout.write(self.style.WARNING('  TRUNCATE TABLE app_supplyhistory CASCADE;'))
            self.stdout.write(self.style.WARNING('  TRUNCATE TABLE app_propertyhistory CASCADE;'))
            self.stdout.write(self.style.WARNING('  TRUNCATE TABLE app_supplyquantity RESTART IDENTITY CASCADE;'))
            self.stdout.write(self.style.WARNING('  TRUNCATE TABLE app_supply RESTART IDENTITY CASCADE;'))
            self.stdout.write(self.style.WARNING('  TRUNCATE TABLE app_property RESTART IDENTITY CASCADE;\n'))
        
        # Create categories first
        self.stdout.write('Creating categories...')
        supply_categories = self.create_supply_categories()
        supply_subcategories = self.create_supply_subcategories()
        property_categories = self.create_property_categories()
        self.stdout.write(self.style.SUCCESS(f'[OK] Created {len(supply_categories)} supply categories'))
        self.stdout.write(self.style.SUCCESS(f'[OK] Created {len(supply_subcategories)} supply subcategories'))
        self.stdout.write(self.style.SUCCESS(f'[OK] Created {len(property_categories)} property categories\n'))
        
        # Populate supplies
        num_supplies = options['supplies']
        self.stdout.write(f'Creating {num_supplies} supply records...')
        supplies_created = self.populate_supplies(num_supplies, supply_categories, supply_subcategories)
        self.stdout.write(self.style.SUCCESS(f'[OK] Created {supplies_created} supply records\n'))
        
        # Populate properties
        num_properties = options['properties']
        self.stdout.write(f'Creating {num_properties} property records...')
        properties_created = self.populate_properties(num_properties, property_categories)
        self.stdout.write(self.style.SUCCESS(f'[OK] Created {properties_created} property records\n'))
        
        # Summary statistics
        self.print_statistics(supplies_created, properties_created)
        
        self.stdout.write(self.style.SUCCESS('\n[OK] Sample data population completed successfully!'))

    def cleanup_data(self):
        """Delete all existing supply and property data"""
        self.stdout.write(self.style.WARNING('Note: This cleanup method has limitations. See --help for manual cleanup instructions.'))
        return

    def create_supply_categories(self):
        """Create supply categories"""
        categories_data = [
            'Office Supplies',
            'IT Equipment',
            'Furniture',
            'Janitorial Supplies',
            'Safety Equipment',
            'Tools & Hardware',
            'Laboratory Equipment',
            'Medical Supplies',
            'Kitchen Supplies',
            'Cleaning Materials',
        ]
        
        categories = []
        for name in categories_data:
            cat, created = SupplyCategory.objects.get_or_create(name=name)
            categories.append(cat)
        
        return categories

    def create_supply_subcategories(self):
        """Create supply subcategories"""
        subcategories_data = [
            'Paper Products',
            'Writing Instruments',
            'Stationery',
            'Computers & Laptops',
            'Monitors & Peripherals',
            'Network Equipment',
            'Office Chairs',
            'Desks & Tables',
            'Storage Cabinets',
            'Mops & Brooms',
            'Soaps & Detergents',
            'Protective Gear',
            'Fire Safety',
            'First Aid',
            'Hand Tools',
            'Power Tools',
            'Microscopes',
            'Test Equipment',
            'Bandages & Gauze',
            'Syringes & Needles',
        ]
        
        subcategories = []
        for name in subcategories_data:
            subcat, created = SupplySubcategory.objects.get_or_create(name=name)
            subcategories.append(subcat)
        
        return subcategories

    def create_property_categories(self):
        """Create property categories with UACS codes"""
        categories_data = [
            ('Computer Equipment', 13124320),
            ('Office Furniture', 15101600),
            ('Vehicles', 16101000),
            ('Laboratory Equipment', 14102300),
            ('Communication Equipment', 16203000),
            ('Medical Equipment', 16202000),
            ('Tools & Equipment', 16101500),
            ('Machinery', 16103000),
            ('Educational Equipment', 14102400),
            ('Electrical Equipment', 16102000),
        ]
        
        categories = []
        for name, uacs in categories_data:
            cat, created = PropertyCategory.objects.get_or_create(
                name=name,
                defaults={'uacs': uacs}
            )
            categories.append(cat)
        
        return categories

    def populate_supplies(self, count, categories, subcategories):
        """Create supply records"""
        supply_names = [
            'A4 Paper Ream', 'Ballpoint Pens', 'Pencils', 'Notepads', 'Sticky Notes',
            'Laptop Computer', 'Desktop Monitor', 'Wireless Mouse', 'Keyboard', 'USB Cable',
            'Office Chair', 'Desk Lamp', 'Filing Cabinet', 'Printer Paper', 'Toner Cartridge',
            'Mop with Handle', 'Broom', 'Cleaning Cloth', 'Disinfectant Spray', 'Hand Soap',
            'Safety Goggles', 'Gloves (Latex)', 'Face Mask', 'First Aid Kit', 'Bandages',
            'Hammer', 'Screwdriver Set', 'Wrench', 'Drill Bit Set', 'Measuring Tape',
            'Microscope', 'Test Tubes', 'Beakers', 'Petri Dishes', 'Pipettes',
            'Stethoscope', 'Blood Pressure Monitor', 'Thermometer', 'Syringes', 'Needles',
            'Coffee Maker', 'Cups & Mugs', 'Sugar Packets', 'Tea Bags', 'Stirrers',
            'Cabinet Lock', 'Door Hinge', 'Electrical Outlet', 'Light Bulb (LED)', 'Batteries (AA)',
            'Extension Cable', 'Power Strip', 'Network Cable', 'HDMI Cable', 'USB Hub',
            'File Folder', 'Envelopes', 'Labels', 'Printer Ink', 'Correction Tape',
            'Desk Organizer', 'Shelf Unit', 'Storage Box', 'Desk Mat', 'Monitor Stand',
            'Hair Net', 'Shoe Covers', 'Apron', 'Chef Hat', 'Food Storage Container',
            'Sanitizer Bottle', 'Disinfectant Wipes', 'Air Freshener', 'Trash Bin', 'Mop Bucket',
        ]
        
        created_count = 0
        for i in range(count):
            try:
                # Select random category and subcategory
                category = random.choice(categories)
                subcategory = random.choice(subcategories)
                
                # Generate unique supply name with index
                supply_name = f"{supply_names[i % len(supply_names)]} - {i+1}"
                
                # Create supply
                supply = Supply.objects.create(
                    supply_name=supply_name,
                    category=category,
                    subcategory=subcategory,
                    description=f"Sample supply item #{i+1} for testing and demonstration purposes",
                    date_received=date.today() - timedelta(days=random.randint(30, 365)),
                    expiration_date=date.today() + timedelta(days=random.randint(30, 365)),
                    available_for_request=random.choice([True, True, True, False]),  # 75% available
                )
                
                # Create quantity record
                current_qty = random.randint(5, 500)
                SupplyQuantity.objects.create(
                    supply=supply,
                    current_quantity=current_qty,
                    reserved_quantity=random.randint(0, current_qty // 2),
                    minimum_threshold=random.randint(5, 50),
                )
                
                created_count += 1
                
                # Progress indicator
                if created_count % 10 == 0:
                    self.stdout.write(f'  [OK] Created {created_count}/{count} supplies')
                    
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  [ERROR] Error creating supply {i+1}: {str(e)}'))
        
        return created_count

    def populate_properties(self, count, categories):
        """Create property records"""
        property_names = [
            'Desktop Computer', 'Laptop', 'Printer', 'Scanner', 'Copy Machine',
            'Office Desk', 'Office Chair', 'Filing Cabinet', 'Bookshelf', 'Conference Table',
            'Honda Civic', 'Toyota Hiace', 'Ford Transit', 'Nissan NV200', 'Isuzu NQR',
            'Microscope', 'Centrifuge', 'Spectrometer', 'Incubator', 'Autoclave',
            'VHF Radio', 'Telephone System', 'Intercom System', 'Two-Way Radio', 'Mobile Phone Charger',
            'CT Scanner', 'X-Ray Machine', 'Ultrasound Machine', 'EKG Machine', 'Defibrillator',
            'Drill', 'Circular Saw', 'Impact Driver', 'Angle Grinder', 'Chop Saw',
            'Industrial Mixer', 'Hydraulic Press', 'Lathe Machine', 'Milling Machine', 'Welder',
            'Projector', 'Interactive Whiteboard', 'Document Camera', 'Audio System', 'Screen',
            'Transformer', 'Generator', 'Inverter', 'Battery Bank', 'Solar Panel',
            'Sofa', 'Armchair', 'Coffee Table', 'Side Table', 'Ottoman',
            'Laptop Bag', 'Backpack', 'File Holder', 'Desk Organizer', 'Wall Clock',
            'Air Conditioner', 'Heater', 'Fan', 'Humidifier', 'Dehumidifier',
            'Water Dispenser', 'Microwave', 'Refrigerator', 'Freezer', 'Ice Maker',
            'Typewriter', 'Calculator', 'Time Clock', 'Safe', 'Cash Register',
        ]
        
        conditions = ['In good condition', 'Needing repair', 'Unserviceable', 'Obsolete']
        locations = [
            'Office A - Floor 1', 'Office B - Floor 1', 'Office C - Floor 2',
            'Warehouse', 'Storage Room', 'Garage', 'Laboratory',
            'Conference Room', 'Break Room', 'Server Room', 'Maintenance Room',
        ]
        
        accountable_persons = [
            'John Smith', 'Maria Garcia', 'Ahmed Hassan', 'Lisa Wong',
            'Robert Johnson', 'Sarah Davis', 'Michael Brown', 'Jennifer Lee',
        ]
        
        created_count = 0
        for i in range(count):
            try:
                # Select random category
                category = random.choice(categories)
                
                # Generate unique property name with index
                property_name = f"{property_names[i % len(property_names)]} - {i+1}"
                
                # Determine if item is available (90% chance of being available)
                condition = random.choice(conditions[:-2]) if random.random() < 0.90 else random.choice(conditions)
                
                # Create property
                property_obj = Property.objects.create(
                    property_number=f"PROP-{str(i+1).zfill(6)}",
                    property_name=property_name,
                    category=category,
                    description=f"Sample property item #{i+1} for testing and demonstration purposes",
                    unit_of_measure=random.choice(['Unit', 'Set', 'Piece', 'Meter', 'Kilogram']),
                    unit_value=round(random.uniform(100, 50000), 2),
                    overall_quantity=random.randint(1, 100),
                    location=random.choice(locations),
                    accountable_person=random.choice(accountable_persons),
                    year_acquired=date(random.randint(2015, 2024), random.randint(1, 12), random.randint(1, 28)),
                    condition=condition,
                )
                
                created_count += 1
                
                # Progress indicator
                if created_count % 10 == 0:
                    self.stdout.write(f'  [OK] Created {created_count}/{count} properties')
                    
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  [ERROR] Error creating property {i+1}: {str(e)}'))
        
        return created_count

    def print_statistics(self, supplies_created, properties_created):
        """Print summary statistics"""
        self.stdout.write('\n' + '='*60)
        self.stdout.write('DATA POPULATION STATISTICS')
        self.stdout.write('='*60)
        
        # Supply statistics
        total_supplies = Supply.objects.count()
        supply_qty_info = SupplyQuantity.objects.all()
        total_supply_qty = sum(sq.current_quantity for sq in supply_qty_info)
        total_reserved = sum(sq.reserved_quantity for sq in supply_qty_info)
        
        self.stdout.write(f'\nSupply Records:')
        self.stdout.write(f'  • Total supplies created: {supplies_created}')
        self.stdout.write(f'  • Total supplies in database: {total_supplies}')
        self.stdout.write(f'  • Total quantity in stock: {total_supply_qty} units')
        self.stdout.write(f'  • Total quantity reserved: {total_reserved} units')
        
        # Category statistics
        supply_categories = SupplyCategory.objects.count()
        supply_subcategories = SupplySubcategory.objects.count()
        
        self.stdout.write(f'  • Supply categories: {supply_categories}')
        self.stdout.write(f'  • Supply subcategories: {supply_subcategories}')
        
        # Property statistics
        total_properties = Property.objects.count()
        total_property_qty = sum(p.overall_quantity for p in Property.objects.all())
        
        self.stdout.write(f'\nProperty Records:')
        self.stdout.write(f'  • Total properties created: {properties_created}')
        self.stdout.write(f'  • Total properties in database: {total_properties}')
        self.stdout.write(f'  • Total property quantity: {total_property_qty} units')
        
        # Property condition breakdown
        condition_breakdown = {}
        for prop in Property.objects.all():
            condition = prop.condition
            condition_breakdown[condition] = condition_breakdown.get(condition, 0) + 1
        
        self.stdout.write(f'  • Property conditions:')
        for condition, count in sorted(condition_breakdown.items()):
            percentage = (count / total_properties * 100) if total_properties > 0 else 0
            self.stdout.write(f'    - {condition}: {count} ({percentage:.1f}%)')
        
        # Property categories
        property_categories = PropertyCategory.objects.count()
        self.stdout.write(f'  • Property categories: {property_categories}')
        
        self.stdout.write('\n' + '='*60)
