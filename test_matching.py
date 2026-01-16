import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ResourceHive.settings')
django.setup()

from app.models import PPMP, PPMPItem, Supply, Department

# Find DCS department and PPMP
dept = Department.objects.filter(name__icontains='DCS').first()
ppmp = PPMP.objects.filter(department=dept, year=2026).first() if dept else None

if ppmp:
    ppmp_items = PPMPItem.objects.filter(ppmp=ppmp)
    
    # Create dict of PPMP items (using unit_measure as the key)
    ppmp_dict = {}
    for item in ppmp_items:
        item_name = item.unit_measure if item.unit_measure else item.description
        if item_name:
            key = item_name.strip().lower()
            ppmp_dict[key] = item
    
    print(f"Total PPMP items: {len(ppmp_dict)}")
    print("\nPPMP Item Names (first 20):")
    for i, name in enumerate(list(ppmp_dict.keys())[:20], 1):
        print(f"  {i}. '{name}'")
    
    # Get supplies
    supplies = Supply.objects.filter(available_for_request=True, quantity_info__current_quantity__gt=0)
    
    print(f"\n\nTotal Available Supplies: {supplies.count()}")
    print("\nSupply Names (first 20):")
    for i, supply in enumerate(supplies[:20], 1):
        print(f"  {i}. '{supply.supply_name}'")
    
    # Try matching
    print("\n\n" + "="*60)
    print("MATCHING ANALYSIS")
    print("="*60)
    
    matches = []
    for supply in supplies:
        supply_key = supply.supply_name.strip().lower()
        
        # Exact match
        if supply_key in ppmp_dict:
            matches.append((supply.supply_name, ppmp_dict[supply_key].unit_measure, 'EXACT'))
            continue
        
        # Partial match
        supply_words = set(supply_key.replace(',', ' ').split())
        for ppmp_key, ppmp_item in ppmp_dict.items():
            ppmp_words = set(ppmp_key.replace(',', ' ').split())
            common = supply_words & ppmp_words
            
            if len(common) >= 2:
                matches.append((supply.supply_name, ppmp_item.unit_measure, f'WORD_MATCH: {common}'))
                break
            elif ppmp_key in supply_key or supply_key in ppmp_key:
                matches.append((supply.supply_name, ppmp_item.unit_measure, 'SUBSTRING'))
                break
    
    print(f"\nTotal Matches: {len(matches)}")
    if matches:
        print("\nMatched Items:")
        for supply_name, ppmp_name, match_type in matches[:20]:
            print(f"  Supply: '{supply_name}'")
            print(f"  PPMP:   '{ppmp_name}'")
            print(f"  Type:   {match_type}")
            print()
    else:
        print("\nNo matches found!")
        print("\nSuggestion: The supply names need to match or contain the PPMP item names.")
        print("For example, if PPMP has 'CORRECTION TAPE', your supply should be named")
        print("'CORRECTION TAPE' or 'Correction Tape' or 'correction tape xyz' to match.")
