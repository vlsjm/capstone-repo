import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ResourceHive.settings')
django.setup()

from app.models import PPMP, PPMPItem, Supply, Department
from datetime import datetime

# Find DCS department
dept = Department.objects.filter(name__icontains='DCS').first()
print(f"Department: {dept}")
print(f"Department ID: {dept.id if dept else 'None'}")
print()

# Find PPMP for 2026
if dept:
    ppmp = PPMP.objects.filter(department=dept, year=2026).first()
    print(f"PPMP for {dept.name} 2026: {ppmp}")
    
    if ppmp:
        items = PPMPItem.objects.filter(ppmp=ppmp)
        print(f"\nTotal PPMP Items: {items.count()}")
        print("\nFirst 10 PPMP Items (with all fields):")
        for i, item in enumerate(items[:10], 1):
            print(f"\n  {i}. Row {item.row_number}:")
            print(f"     Description: '{item.description}'")
            print(f"     Common Office Supplies: '{item.common_office_supplies}'")
            print(f"     Office Supplies Expense: '{item.office_supplies_expense}'")
            print(f"     Supplies Materials Expense: '{item.supplies_materials_expense}'")
            print(f"     Unit Measure: '{item.unit_measure}'")
            print(f"     Quantity: {item.quantity}")
    else:
        print("No PPMP found for DCS 2026")
        # Check what PPMPs exist
        all_ppmps = PPMP.objects.all()
        print(f"\nAll PPMPs in database:")
        for p in all_ppmps:
            print(f"  - {p.department.name} {p.year}")
else:
    print("DCS Department not found")
    print("\nAll Departments:")
    for d in Department.objects.all():
        print(f"  - {d.name}")

print("\n" + "="*50)
print("First 10 Available Supplies:")
supplies = Supply.objects.filter(available_for_request=True, quantity_info__current_quantity__gt=0)[:10]
for i, s in enumerate(supplies, 1):
    print(f"  {i}. '{s.supply_name}' (ID: {s.id})")
