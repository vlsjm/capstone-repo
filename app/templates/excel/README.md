# Excel Template for Properties Above ₱50,000

## Template Location
Place your Excel template file here:
`app/templates/excel/property_above_50k_template.xlsx`

## Template Structure Guide

Your Excel template should have **ONE CATEGORY TABLE** that will be replicated for each category.

### Important Concepts

The system will:
1. Use your template table for the first category
2. **Copy** and insert the template table for each additional category
3. Stack all category tables vertically in the output file
4. Replace "PPE Account group" with "UACS - CATEGORY NAME" for each category

### Required Template Structure

**Rows 1-5**: Header Information (optional)
- Title, institution name, report date, etc.
- These will appear only once at the top

**Row 6**: Category Header Row
- This row should contain the "PPE Account group" or similar label
- The system will replace this with "UACS - CATEGORY NAME"
- Example: Cell B6 might contain "PPE Account group:"
- Will become: "13124324 - Office Equipment"

**Row 7**: Column Headers
- Item No. | Property # | Name | Description | Value | Qty | Location | Person | Year | Condition
- These headers will be copied for each category table

**Rows 8-10**: Sample Data Rows (optional)
- You can have a few sample rows with formatting
- These will be used as a template for styling
- The actual data will replace these rows

### Template Configuration Variables

You need to tell the system about your template structure by adjusting these variables in `views.py`:

```python
template_start_row = 6   # Row where the category header is (PPE Account group)
template_data_row = 7    # Row where column headers are
template_row_count = 10  # Total rows in one category table (including headers and spacing)
```

### UACS - Category Name Format

The category header will be formatted as:
- **With UACS**: `13124324 - Office Equipment`
- **Without UACS**: `N/A - Office Equipment`
- **Uncategorized items**: `N/A - Uncategorized`

Update this cell reference in the code based on where your template shows "PPE Account group":
```python
ws[f'B{category_header_row}'] = category_label  # Change 'B' to your column
```

### Column Mapping

Current mapping for data rows:

| Column | Field                | Description                                    |
|--------|----------------------|------------------------------------------------|
| A      | Item Number          | Sequential number (continuous across categories)|
| B      | Property Number      | Unique property identifier                     |
| C      | Property Name        | Name of the property                           |
| D      | Description          | Detailed description                           |
| E      | Unit Value           | Value per unit (will be > ₱50,000)            |
| F      | Quantity             | Current quantity available                     |
| G      | Location             | Storage/assignment location                    |
| H      | Accountable Person   | Person responsible for the property            |
| I      | Year Acquired        | Year the property was acquired (YYYY format)   |
| J      | Condition            | Current condition of the property              |

### Example Template Structure

```
Row 1:  PROPERTY REPORT - HIGH VALUE ITEMS (Above ₱50,000)
Row 2:  [Your Institution Name]
Row 3:  Report Date: October 13, 2025
Row 4:  
Row 5:  
Row 6:  PPE Account group: [Will be replaced with UACS - Category Name]
Row 7:  No. | Property # | Name | Description | Value | Qty | Location | Person | Year | Condition
Row 8:  [Sample data row 1]
Row 9:  [Sample data row 2]
Row 10: [Blank spacing row]
```

### How It Works

1. **First Category (e.g., Office Equipment)**
   - Uses the original template (rows 6-10)
   - Row 6: "13124324 - Office Equipment"
   - Rows 7+: Column headers + actual data

2. **Second Category (e.g., Computer Equipment)**
   - Template is copied and inserted below the first category
   - Row X: "13124325 - Computer Equipment"
   - Rows X+1+: Column headers + actual data

3. **Third Category, etc.**
   - Process repeats for each category

### Output Example

```
[Header Section - Once]
PROPERTY REPORT - HIGH VALUE ITEMS

PPE Account group: 13124324 - Office Equipment
No. | Property # | Name        | Description | Value    | ...
1   | PROP-001   | Desk        | Wood desk   | 55,000   | ...
2   | PROP-002   | Cabinet     | Steel       | 60,000   | ...

PPE Account group: 13124325 - Computer Equipment  
No. | Property # | Name        | Description | Value    | ...
3   | PROP-010   | Laptop      | Dell XPS    | 75,000   | ...
4   | PROP-011   | Server      | HP ProLiant | 150,000  | ...

PPE Account group: 13124326 - Furniture
No. | Property # | Name        | Description | Value    | ...
5   | PROP-020   | Conference  | 10-seater   | 80,000   | ...
```

### Customizing Row/Column Positions

To match your specific template, adjust these in the `export_property_above_50k` function:

1. **Category header position:**
   ```python
   ws[f'B{category_header_row}'] = category_label
   # Change 'B' to the column where "PPE Account group" appears
   ```

2. **Data starting position:**
   ```python
   data_start_row = current_row + 1
   # Adjust the +1 offset based on how many rows after category header
   ```

3. **Column assignments:**
   ```python
   ws[f'A{row}'] = overall_item_number  # Item number
   ws[f'B{row}'] = prop.property_number  # Change letter to match your template
   ws[f'C{row}'] = prop.property_name    # Change letter to match your template
   # ... etc.
   ```

### Testing Checklist

- [ ] Template file is in correct location
- [ ] Category header shows "UACS - Category Name" format
- [ ] Each category has its own table section
- [ ] Tables are properly spaced vertically
- [ ] Item numbers continue sequentially across categories
- [ ] Formatting is preserved from template
- [ ] All data appears in correct columns

### Troubleshooting

**Categories appearing in wrong rows:**
- Adjust `template_start_row` to match where your category table begins
- Adjust `template_row_count` to include all rows of one category table

**Data in wrong columns:**
- Update column letters (A, B, C, etc.) in the code to match your template

**Category name not showing:**
- Check that `ws[f'B{category_header_row}']` matches where "PPE Account group" is in your template

**Formatting not copying:**
- Ensure your template has proper cell formatting
- Check that `template_row_count` covers all formatted rows
