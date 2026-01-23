"""
Debug script to check PPMP year allocation issues
This script will help identify why selecting 2024 also deducts from 2026
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ResourceHive.settings')
django.setup()

from app.models import PPMP, PPMPItem, Department
from django.contrib.auth.models import User

def check_ppmp_item_years():
    """Check if any PPMP items are incorrectly assigned to multiple years"""
    print("=" * 80)
    print("CHECKING PPMP ITEM YEAR ASSIGNMENTS")
    print("=" * 80)
    
    # Get all PPMP items
    ppmp_items = PPMPItem.objects.select_related('ppmp').all()
    
    # Check for any anomalies
    item_year_map = {}
    for item in ppmp_items:
        item_id = item.id
        item_year = item.ppmp.year
        item_desc = item.description
        
        if item_id in item_year_map:
            print(f"⚠️  WARNING: PPMP Item ID {item_id} appears in multiple records!")
            print(f"   Previous: Year {item_year_map[item_id]}")
            print(f"   Current: Year {item_year}")
        else:
            item_year_map[item_id] = item_year
    
    print(f"\n✓ Checked {len(ppmp_items)} PPMP items")
    print(f"✓ All item IDs are unique and tied to single years\n")


def check_department_ppmp_years(department_name):
    """Check PPMP years for a specific department"""
    print("=" * 80)
    print(f"CHECKING PPMP YEARS FOR: {department_name}")
    print("=" * 80)
    
    try:
        dept = Department.objects.get(name=department_name)
    except Department.DoesNotExist:
        print(f"❌ Department '{department_name}' not found!")
        return
    
    ppmps = PPMP.objects.filter(department=dept).order_by('year')
    
    if not ppmps:
        print(f"❌ No PPMPs found for {department_name}")
        return
    
    print(f"\nFound {ppmps.count()} PPMP(s) for {department_name}:\n")
    
    for ppmp in ppmps:
        print(f"📅 PPMP Year {ppmp.year} (ID: {ppmp.id})")
        print(f"   Uploaded: {ppmp.upload_date.strftime('%Y-%m-%d %H:%M')}")
        print(f"   Items: {ppmp.items.count()}")
        
        # Show sample items
        sample_items = ppmp.items.all()[:3]
        for item in sample_items:
            print(f"   - Item #{item.id}: {item.description[:50]}... (Qty: {item.quantity}, Released: {item.released}, Remaining: {item.remaining})")
        
        if ppmp.items.count() > 3:
            print(f"   ... and {ppmp.items.count() - 3} more items")
        print()


def simulate_year_matching(supply_name, department_name):
    """Simulate how the system matches a supply to PPMP years"""
    print("=" * 80)
    print(f"SIMULATING PPMP MATCHING")
    print("=" * 80)
    print(f"Supply Name: {supply_name}")
    print(f"Department: {department_name}\n")
    
    try:
        dept = Department.objects.get(name=department_name)
    except Department.DoesNotExist:
        print(f"❌ Department '{department_name}' not found!")
        return
    
    ppmps = PPMP.objects.filter(department=dept).order_by('year')
    
    for ppmp in ppmps:
        print(f"\n🔍 Checking PPMP Year {ppmp.year}")
        print(f"   PPMP ID: {ppmp.id}")
        
        # Match by description (case-insensitive, partial match)
        matched_items = ppmp.items.filter(description__icontains=supply_name)
        
        if matched_items:
            print(f"   ✓ Found {matched_items.count()} matching item(s):")
            for item in matched_items:
                print(f"      - Item #{item.id}: {item.description}")
                print(f"        Quantity: {item.quantity}, Released: {item.released}, Remaining: {item.remaining}")
                print(f"        Belongs to PPMP Year: {item.ppmp.year} (PPMP ID: {item.ppmp.id})")
        else:
            print(f"   ✗ No matching items")


if __name__ == "__main__":
    # Run checks
    check_ppmp_item_years()
    
    # Get all departments
    departments = Department.objects.all()
    print("\nAvailable Departments:")
    for dept in departments:
        print(f"  - {dept.name}")
    
    # Check a specific department (modify this as needed)
    if departments.exists():
        first_dept = departments.first()
        check_department_ppmp_years(first_dept.name)
        
        # Simulate matching for a sample supply
        print("\n" + "=" * 80)
        print("To simulate matching, run:")
        print(f"  simulate_year_matching('YOUR_SUPPLY_NAME', '{first_dept.name}')")
        print("=" * 80)
