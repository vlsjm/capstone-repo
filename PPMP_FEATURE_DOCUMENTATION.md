# PPMP (Project Procurement Management Plan) Feature Implementation

## Overview
This feature allows administrators to upload department PPMP forms in Excel format and automatically cross-checks supply requests against the uploaded PPMP data.

## Features Implemented

### 1. PPMP Upload System
- **Location**: Admin Panel → PPMP Management
- **File Format**: Excel (.xlsx, .xls)
- **Required Sheet**: "3- 2025 PPMP FORM" (or any sheet containing "PPMP FORM")
- **Department Association**: Each PPMP is linked to a specific department
- **Year Tracking**: One PPMP per department per year

### 2. PPMP Data Storage
Two new models were created:
- **PPMP Model**: Stores uploaded files with department and year association
- **PPMPItem Model**: Stores individual line items from the Excel sheet

#### Captured Fields from Excel:
- Unit (Campus/Office)
- Mode (MOOE, etc.)
- Supplies and Materials Expense categories
- **Description** (primary item identifier)
- Unit of Measure (PC, Box, Bundle, etc.)
- Unit Price
- Quantity
- Total Amount
- Source of Fund
- Row Number (for reference)

### 3. PPMP Display & Management
- **List View**: Shows all uploaded PPMPs with filtering by department and year
- **Detail View**: Displays all items in a PPMP with search functionality
- **Delete Function**: Remove PPMPs and all associated items
- **Pagination**: 50 items per page for easy navigation

### 4. Automatic PPMP Cross-Checking
When an admin reviews a supply request for approval:
- The system automatically checks if the requested item matches any entry in the requester's department PPMP
- **Match Found**: Green badge displays "✓ Found X matching item(s) in [Department] PPMP [Year]"
- **No Match**: Yellow badge displays "⚠ No matching items found in [Department] PPMP [Year]"
- **No PPMP**: Yellow badge displays "⚠ No PPMP found for [Department] for year [Year]"

The matching is based on:
- **Department**: Requester's department
- **Year**: Request year
- **Item Description**: Case-insensitive partial match

### 5. Navigation
Added "PPMP Management" to the main sidebar navigation menu

## Files Created/Modified

### New Files:
1. `app/templates/app/ppmp_upload.html` - Upload interface
2. `app/templates/app/ppmp_list.html` - List of all PPMPs
3. `app/templates/app/ppmp_detail.html` - Detailed view of PPMP items
4. `app/templates/app/ppmp_delete_confirm.html` - Delete confirmation
5. `app/templates/app/includes/sidebar.html` - Reusable sidebar component
6. `app/migrations/0100_ppmp_ppmpitem.py` - Database migration

### Modified Files:
1. `app/models.py` - Added PPMP and PPMPItem models
2. `app/forms.py` - Added PPMPUploadForm
3. `app/views.py` - Added PPMP views and modified batch_request_detail
4. `app/urls.py` - Added PPMP URL patterns
5. `app/utils.py` - Added parse_ppmp_excel() and check_ppmp_match()
6. `app/admin.py` - Registered PPMP models in admin
7. `app/templatetags/user_filters.py` - Added get_item filter
8. `app/templates/app/navbar.html` - Added PPMP menu item
9. `app/templates/app/batch_request_detail.html` - Added PPMP match display

## How to Use

### Uploading a PPMP:
1. Navigate to "PPMP Management" in the sidebar
2. Click "Upload New PPMP"
3. Select the department
4. Enter the year
5. Choose the Excel file
6. Click "Upload and Parse"
7. System will automatically extract all items from the Excel sheet

### Viewing PPMP Data:
1. Go to "PPMP Management"
2. Use filters to find specific department/year
3. Click "View Details" to see all items
4. Use search to find specific items

### During Request Approval:
When reviewing supply requests in the batch request detail page:
- PPMP match indicators automatically appear below each item
- Green badge = Item is in the PPMP (aligned with department plan)
- Yellow badge = Item not in PPMP or no PPMP exists (may need justification)

## Technical Details

### Excel Parsing:
- Uses `openpyxl` library (already in requirements.txt)
- Starts reading from row 23 (configurable in `parse_ppmp_excel()`)
- Skips empty rows automatically
- Handles missing/null values gracefully

### Matching Algorithm:
- Case-insensitive search
- Partial string matching (e.g., "ERASER" matches "ERASER, FELT, 10 beads")
- Only checks against the requester's department PPMP
- Uses the request year for PPMP lookup

### Permissions:
- Only users with `approve_supply_request` permission can:
  - Upload PPMPs
  - View PPMP lists
  - Delete PPMPs

### Database Constraints:
- `unique_together` on PPMP model: (department, year)
- Ensures only one PPMP per department per year
- Cascade delete: Deleting PPMP removes all associated items

## Future Enhancements (Optional)

1. **Export PPMP Data**: Add ability to export filtered items to Excel
2. **PPMP Templates**: Provide downloadable PPMP Excel templates
3. **Bulk Upload**: Upload multiple PPMP files at once
4. **Budget Tracking**: Track approved vs planned budget from PPMP
5. **Alerts**: Notify admins when requests exceed PPMP quantities
6. **Reports**: Generate department spending vs PPMP reports
7. **PPMP Amendments**: Allow updating existing PPMPs
8. **Multi-year Comparison**: Compare PPMP across years

## Notes

- The feature only applies to **supply requests** (not property/borrow requests)
- The PPMP matching is informational only - it doesn't prevent approval
- Files are stored in `media/ppmp_files/` directory
- The system preserves the original Excel file for reference
