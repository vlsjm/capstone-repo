# CvSU Inventory Count Form - Implementation Guide

## Overview
This guide explains the implementation of the Excel Inventory Count Form that matches the Cavite State University (CvSU) format. The form is designed to export property inventory data for items valued above ₱50,000.

## Features

### 1. **Automatic Filtering**
- Only includes properties with `unit_value > 50,000 pesos`
- Excludes all properties below the threshold

### 2. **Grouped by PPE Account Group**
- Properties are automatically grouped by their category (PPE Account Group)
- Each category gets its own sheet in the Excel workbook
- Each sheet displays:
  - UACS code (if available)
  - Category name

### 3. **Official CvSU Header**
The header on each sheet includes:
- **Republic of the Philippines**
- **CAVITE STATE UNIVERSITY**
- **Don Severino de las Alas Campus**
- **Indang, Cavite**
- **www.cvsu.edu.ph**
- **CvSU Logo** (centered at the top)
- **"Inventory Count Form"** title
- **PPE Account Group** with UACS code and category name

### 4. **Complete Table Structure**
Each sheet contains a table with the following columns:

| Column | Description |
|--------|-------------|
| Article/Item | Property name |
| Description | Detailed description of the property |
| Old Property No. assigned | Previous property number (if changed) |
| New Property No. assigned | Current property number |
| Unit of Measure | Measurement unit |
| Unit Value | Formatted as currency (₱) |
| Quantity per Property Count | Recorded quantity in property records |
| Quantity per Physical Count | Physical inventory count quantity |
| Location/Whereabouts | Building, Floor and Room No. |
| Condition | Good condition, needing repair, unserviceable, obsolete, etc. |
| Remarks | For manual entry (Non-existing or Missing) |

### 5. **Professional Formatting**
- Consistent borders on all cells
- Centered and wrapped headers
- Proper column widths for readability
- Row heights adjusted for multi-line content
- Number formatting for currency values
- Professional fonts (Calibri)

## How to Use

### From the Web Interface

1. **Navigate to Property Management**
   - Log in to the admin panel
   - Go to the Property page

2. **Open Export Modal**
   - Click the **Actions** dropdown (three dots icon)
   - Select **"Export to Excel"**

3. **Select the CvSU Inventory Count Form**
   - In the Export Modal, select the radio option:
     - **📋 CvSU Inventory Count Form (Above ₱50,000.00)**

4. **Generate the Report**
   - Click **"Generate CvSU Inventory Count Form"**
   - The file will download automatically

### File Output

**Filename Format:**
```
Inventory_Count_Over50k_YYYYMMDD_HHMMSS.xlsx
```

**Example:**
```
Inventory_Count_Over50k_20251019_143022.xlsx
```

## Technical Implementation

### Backend (views.py)

**Function:** `export_inventory_count_form_cvsu()`

**Location:** `app/views.py` (after line 4250)

**Key Libraries Used:**
- `openpyxl` - Excel file generation
- `PIL (Pillow)` - Image handling for logo
- `collections.OrderedDict` - Maintain category ordering

**Process Flow:**
1. Query properties where `unit_value > 50000`
2. Group properties by category (PPE Account Group)
3. Create separate sheet for each category
4. Add CvSU header with logo
5. Add PPE Account Group label
6. Create table with headers
7. Populate data rows
8. Apply formatting (borders, fonts, alignment)
9. Return Excel file as HTTP response

### Frontend (property.html)

**Changes Made:**
1. Added new radio option in Export Modal
2. Updated JavaScript to handle new export format
3. Dynamic form action URL switching

**JavaScript Handler:**
```javascript
else if (this.value === 'inventory_count_cvsu') {
    excelFieldsSection.style.display = 'none';
    pdfFieldsSection.style.display = 'none';
    generateReportBtn.innerHTML = '<i class="fas fa-file-excel"></i> Generate CvSU Inventory Count Form';
    exportForm.action = "{% url 'export_inventory_count_form_cvsu' %}";
}
```

### URL Configuration (urls.py)

**Endpoint:** `/export-inventory-count-form/`

**URL Name:** `export_inventory_count_form_cvsu`

**Import Added:**
```python
from .views import export_inventory_count_form_cvsu
```

**URL Pattern:**
```python
path('export-inventory-count-form/', export_inventory_count_form_cvsu, name='export_inventory_count_form_cvsu'),
```

## Column Specifications

### Column Widths (in Excel units)
- A (Article/Item): 18
- B (Description): 25
- C (Old Property No.): 15
- D (New Property No.): 15
- E (Unit of Measure): 10
- F (Unit Value): 12
- G (Qty per Property Count): 10
- H (Qty per Physical Count): 10
- I (Location): 20
- J (Condition): 15
- K (Remarks): 15

### Row Heights
- Header row: 60 points (for wrapped text)
- Data rows: 30 points

## Logo Requirements

**Location:** `static/images/cvsu logo.png`

**Specifications:**
- Format: PNG
- Size: Auto-scaled to 60x60 pixels
- Position: F1 cell (upper center area)

**Fallback:** If logo file is not found, the header will still render correctly without the logo.

## Data Mapping

| Database Field | Excel Column |
|---------------|--------------|
| `property_name` | Article/Item |
| `description` | Description |
| `old_property_number` | Old Property No. assigned |
| `property_number` | New Property No. assigned |
| `unit_of_measure` | Unit of Measure |
| `unit_value` | Unit Value (formatted as #,##0.00) |
| `quantity` | Quantity per Property Count |
| `quantity_per_physical_count` | Quantity per Physical Count |
| `location` | Location/Whereabouts |
| `condition` | Condition |
| - | Remarks (empty for manual entry) |

## Category Grouping

**Grouping Logic:**
```python
properties_by_category = OrderedDict()
for prop in properties:
    if prop.category:
        category_key = prop.category.id
        if category_key not in properties_by_category:
            properties_by_category[category_key] = {
                'category': prop.category,
                'properties': []
            }
        properties_by_category[category_key]['properties'].append(prop)
```

**Sheet Naming:**
- Sheet names are limited to 25 characters (Excel limitation: 31 chars max)
- Uses category name
- Uncategorized properties go to "Uncategorized" sheet

**PPE Account Group Label Format:**
```
PPE Account Group: {UACS_CODE} - {CATEGORY_NAME}
```

**Example:**
```
PPE Account Group: 10605020 - Office Equipment
```

## Testing Checklist

### Pre-Export Checks
- [ ] Properties with `unit_value > 50000` exist in database
- [ ] Properties have categories assigned
- [ ] Logo file exists at `static/images/cvsu logo.png`
- [ ] User is logged in with proper permissions

### Post-Export Validation
- [ ] File downloads successfully
- [ ] Filename matches expected format
- [ ] Multiple sheets created (one per category)
- [ ] Header appears on all sheets
- [ ] Logo is visible and properly sized
- [ ] PPE Account Group label is correct
- [ ] Table headers are properly formatted
- [ ] Data rows contain correct information
- [ ] Currency values are formatted correctly
- [ ] Borders are applied to all cells
- [ ] Column widths are appropriate
- [ ] Text wrapping works in headers

## Troubleshooting

### Issue: Logo Not Displaying
**Solution:** Ensure `static/images/cvsu logo.png` exists. The export will work without the logo, but it won't match the sample exactly.

### Issue: No Data in Export
**Solution:** Verify that properties exist with `unit_value > 50000`
```sql
SELECT COUNT(*) FROM app_property WHERE unit_value > 50000;
```

### Issue: Categories Not Showing
**Solution:** Ensure properties have categories assigned:
```sql
SELECT * FROM app_property WHERE category_id IS NULL AND unit_value > 50000;
```

### Issue: Export Button Not Working
**Solution:** Check browser console for JavaScript errors. Ensure URL is properly configured in `urls.py`.

## Sample Output Structure

```
Inventory_Count_Over50k_20251019_143022.xlsx
│
├── Sheet 1: Office Equipment
│   ├── Header (Rows 1-7)
│   │   ├── Republic of the Philippines
│   │   ├── CAVITE STATE UNIVERSITY
│   │   ├── Don Severino de las Alas Campus
│   │   ├── Indang, Cavite
│   │   ├── www.cvsu.edu.ph
│   │   ├── Logo (F1)
│   │   └── Inventory Count Form
│   ├── PPE Account Group (Row 9)
│   ├── Table Headers (Row 11)
│   └── Data Rows (Row 12+)
│
├── Sheet 2: Furniture and Fixtures
│   └── [Same structure as Sheet 1]
│
└── Sheet N: [Other categories]
    └── [Same structure as Sheet 1]
```

## Future Enhancements

### Potential Improvements
1. **Signature Section:** Add signature blocks at the bottom
2. **Date Range Filter:** Allow filtering by acquisition date
3. **Custom Campus Info:** Make campus details configurable
4. **Barcode Integration:** Include barcode images in the export
5. **Summary Page:** Add a summary sheet with totals by category
6. **Conditional Formatting:** Highlight discrepancies between property count and physical count
7. **PDF Version:** Create a PDF variant of the form

## Dependencies

```txt
Django==5.2.1
openpyxl==3.1.5
pillow==11.2.1
```

## Permissions Required

- User must be logged in (`@login_required`)
- No specific permission checks (can be added if needed)

## Database Models Used

- `Property` - Main property model
- `PropertyCategory` - Category with UACS code

## References

- Sample Image: Cavite State University Inventory Count Form
- Location: Provided in project requirements
- Format: Official CvSU format for properties > ₱50,000

---

**Implementation Date:** October 19, 2025  
**Version:** 1.0  
**Author:** Development Team  
**Status:** ✅ Complete and Ready for Use
