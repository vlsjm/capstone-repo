# Quick Configuration Guide

## Step 1: Analyze Your Template

Open your Excel template and note:

1. **What row has "PPE Account group"?** _____ (e.g., 6)
2. **What column has "PPE Account group"?** _____ (e.g., B)
3. **What row has the column headers?** _____ (e.g., 7)
4. **How many total rows does one category table occupy?** _____ (e.g., 10)
5. **What row should data start?** _____ (e.g., 8)

## Step 2: Update Configuration in views.py

Find the `export_property_above_50k` function and update these lines:

```python
# Line ~3592: Update these values based on your template
template_start_row = 6   # Change to your answer from Question 1
template_data_row = 7    # Change to your answer from Question 3
template_row_count = 10  # Change to your answer from Question 4

# Line ~3628: Update category header cell
ws[f'B{category_header_row}'] = category_label  # Change 'B' to your answer from Question 2

# Line ~3631: Update data start row offset
data_start_row = current_row + 1  # Adjust +1 if headers are in different position
```

## Step 3: Update Column Mappings

Based on which columns in your template correspond to each field:

```python
# Line ~3636-3646: Update these column letters
ws[f'A{row}'] = overall_item_number      # Item number column
ws[f'B{row}'] = prop.property_number     # Property number column
ws[f'C{row}'] = prop.property_name       # Property name column
ws[f'D{row}'] = prop.description or ''   # Description column
ws[f'E{row}'] = prop.unit_value          # Unit value column
ws[f'F{row}'] = prop.quantity or 0       # Quantity column
ws[f'G{row}'] = prop.location or ''      # Location column
ws[f'H{row}'] = prop.accountable_person or ''  # Person column
ws[f'I{row}'] = prop.year_acquired.strftime('%Y') if prop.year_acquired else ''  # Year column
ws[f'J{row}'] = prop.condition or ''     # Condition column
```

## Example Configuration

If your template has:
- Row 8: "PPE Account group:" in column C
- Row 9: Column headers
- Row 10-15: Data and spacing (6 rows total per category)

Then configure:
```python
template_start_row = 8
template_data_row = 9
template_row_count = 6

# And update:
ws[f'C{category_header_row}'] = category_label  # Changed from B to C

data_start_row = current_row + 1  # Headers are 1 row after category header
```

## Testing Your Configuration

1. Run the export with test data
2. Check:
   - ✓ First category appears in correct position
   - ✓ Category shows as "UACS - Name"
   - ✓ Second category appears below first
   - ✓ Data is in correct columns
   - ✓ Formatting is preserved
   
3. If something is wrong, adjust the configuration values and try again

## Common Issues & Fixes

| Issue | Fix |
|-------|-----|
| Categories overlap | Increase `template_row_count` |
| Too much space between categories | Decrease the `+ 2` in `current_row += rows_used + 2` |
| Data starts in wrong row | Adjust `data_start_row = current_row + X` |
| Category label in wrong cell | Change column letter in `ws[f'B{category_header_row}']` |
| Data in wrong columns | Update column letters in mapping section |
